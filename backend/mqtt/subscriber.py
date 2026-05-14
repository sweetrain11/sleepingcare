"""
mqtt/subscriber.py
MQTT 브로커 구독 → 센서 데이터 DB 저장
수면 이벤트(sleep_start / sleep_end / sleep_resume) 처리
"""
import json
import asyncio
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from core.config import settings
from core.database import get_pool
from services.sleep_score import calc_total_score

logger = logging.getLogger(__name__)

# --------------------------------------------------
# 토픽 상수
# --------------------------------------------------
TOPIC_PREFIX = "sleepingcare"
SENSOR_TOPICS = [
    f"{TOPIC_PREFIX}/sensors/temperature",
    f"{TOPIC_PREFIX}/sensors/humidity",
    f"{TOPIC_PREFIX}/sensors/light",
    f"{TOPIC_PREFIX}/sensors/sound",
    f"{TOPIC_PREFIX}/sensors/motion",
    f"{TOPIC_PREFIX}/sensors/time",
]
EVENT_TOPICS = [
    f"{TOPIC_PREFIX}/events/sleep_start",
    f"{TOPIC_PREFIX}/events/sleep_end",
    f"{TOPIC_PREFIX}/events/sleep_resume",
]

# --------------------------------------------------
# 인메모리 센서 버퍼 (time 기준으로 세트 묶음)
# --------------------------------------------------
_sensor_buffer: dict = {}
_loop: asyncio.AbstractEventLoop | None = None


def _parse_payload(payload: bytes):
    """MQTT 페이로드 파싱 (JSON 또는 단순 값)"""
    text = payload.decode("utf-8").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 숫자 또는 문자열 단순값
        try:
            return float(text)
        except ValueError:
            return text


async def _save_sensor_data(data: dict):
    """센서 데이터 DB 저장"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sensor_data
                (time, arduino_time, temperature, humidity, light, sound, motion)
            VALUES
                (NOW(), $1, $2, $3, $4, $5, $6)
            """,
            data.get("arduino_time"),
            data.get("temperature"),
            data.get("humidity"),
            data.get("light"),
            data.get("sound"),
            bool(data.get("motion", False)),
        )
    logger.debug("센서 데이터 저장 완료")


async def _handle_sleep_start(timestamp: datetime | None):
    """수면 시작 이벤트 → sleep_sessions 레코드 생성"""
    pool = await get_pool()
    ts = timestamp or datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(
            "INSERT INTO sleep_sessions (start_time) VALUES ($1) RETURNING id",
            ts,
        )
    logger.info(f"수면 세션 시작: id={session_id}, start_time={ts}")


async def _handle_sleep_end(timestamp: datetime | None):
    """
    수면 종료 이벤트
    - 진행 중인 세션(end_time IS NULL) 찾아 종료
    - 세션 구간 센서 평균 집계
    - 점수 산출 후 DB 업데이트
    """
    pool = await get_pool()
    ts = timestamp or datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        # 가장 최근 미종료 세션 조회
        session = await conn.fetchrow(
            "SELECT id, start_time FROM sleep_sessions WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
        )
        if not session:
            logger.warning("종료할 수면 세션 없음")
            return

        session_id = session["id"]
        start_time = session["start_time"]
        duration_min = int((ts - start_time).total_seconds() / 60)

        # 세션 구간 센서 평균 집계
        agg = await conn.fetchrow(
            """
            SELECT
                AVG(temperature)    AS avg_temperature,
                AVG(humidity)       AS avg_humidity,
                AVG(light)          AS avg_light,
                AVG(sound)          AS avg_sound,
                COUNT(*) FILTER (WHERE motion = TRUE) AS motion_count
            FROM sensor_data
            WHERE time BETWEEN $1 AND $2
            """,
            start_time, ts,
        )

        avg_temp   = float(agg["avg_temperature"]) if agg["avg_temperature"] else None
        avg_hum    = float(agg["avg_humidity"])    if agg["avg_humidity"]    else None
        avg_light  = float(agg["avg_light"])       if agg["avg_light"]       else None
        avg_sound  = float(agg["avg_sound"])       if agg["avg_sound"]       else None
        motion_cnt = int(agg["motion_count"])      if agg["motion_count"]    else 0

        # 규칙성: 직전 세션과 취침 시각 비교
        prev = await conn.fetchrow(
            """
            SELECT start_time FROM sleep_sessions
            WHERE id != $1 AND end_time IS NOT NULL
            ORDER BY start_time DESC LIMIT 1
            """,
            session_id,
        )
        regularity_diff = None
        if prev:
            prev_start = prev["start_time"]
            # 같은 시간대 기준 분 단위 차이
            regularity_diff = int(
                abs(
                    (start_time.hour * 60 + start_time.minute)
                    - (prev_start.hour * 60 + prev_start.minute)
                )
            )

        # 점수 계산
        env_score, pattern_score, total_score = calc_total_score(
            avg_temp, avg_hum, avg_light, avg_sound,
            duration_min, regularity_diff, motion_cnt,
        )

        # 세션 업데이트
        await conn.execute(
            """
            UPDATE sleep_sessions SET
                end_time            = $1,
                duration_min        = $2,
                avg_temperature     = $3,
                avg_humidity        = $4,
                avg_light           = $5,
                avg_sound           = $6,
                motion_count        = $7,
                regularity_diff_min = $8,
                env_score           = $9,
                pattern_score       = $10,
                total_score         = $11
            WHERE id = $12
            """,
            ts, duration_min,
            avg_temp, avg_hum, avg_light, avg_sound,
            motion_cnt, regularity_diff,
            env_score, pattern_score, total_score,
            session_id,
        )

    logger.info(
        f"수면 세션 종료: id={session_id}, "
        f"duration={duration_min}min, total={total_score}점"
    )


async def _handle_sleep_resume(timestamp: datetime | None):
    """
    수면 재개 이벤트 (종료 후 5분 내 다시 수면)
    → 직전 세션 end_time 초기화 (재개 처리)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sleep_sessions
            SET end_time = NULL, duration_min = NULL,
                env_score = NULL, pattern_score = NULL, total_score = NULL
            WHERE id = (
                SELECT id FROM sleep_sessions
                ORDER BY start_time DESC LIMIT 1
            )
            """
        )
    logger.info("수면 재개: 직전 세션 종료 취소")


# --------------------------------------------------
# MQTT 콜백
# --------------------------------------------------

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT 브로커 연결 성공")
        for topic in SENSOR_TOPICS + EVENT_TOPICS:
            client.subscribe(topic)
            logger.debug(f"구독: {topic}")
    else:
        logger.error(f"MQTT 연결 실패: rc={rc}")


def _on_message(client, userdata, msg):
    """메시지 수신 → asyncio 이벤트 루프에 코루틴 예약"""
    global _loop
    if _loop is None:
        return

    topic = msg.topic
    payload = _parse_payload(msg.payload)

    asyncio.run_coroutine_threadsafe(
        _dispatch(topic, payload), _loop
    )


async def _dispatch(topic: str, payload):
    """토픽별 처리 분기"""
    # ── 센서 데이터 버퍼링 ──────────────────────────
    if topic.startswith(f"{TOPIC_PREFIX}/sensors/"):
        sensor_key = topic.split("/")[-1]  # temperature | humidity | ...

        if sensor_key == "time":
            # arduino_time 수신 시 버퍼 flush (한 세트 완성)
            _sensor_buffer["arduino_time"] = payload
            await _flush_sensor_buffer()
        else:
            if sensor_key == "motion":
                _sensor_buffer[sensor_key] = bool(payload)
            elif sensor_key in ("light", "sound"):
                _sensor_buffer[sensor_key] = int(payload) if payload is not None else None
            else:
                _sensor_buffer[sensor_key] = float(payload) if payload is not None else None

    # ── 수면 이벤트 ─────────────────────────────────
    elif topic == f"{TOPIC_PREFIX}/events/sleep_start":
        ts = _parse_event_time(payload)
        await _handle_sleep_start(ts)

    elif topic == f"{TOPIC_PREFIX}/events/sleep_end":
        ts = _parse_event_time(payload)
        await _handle_sleep_end(ts)

    elif topic == f"{TOPIC_PREFIX}/events/sleep_resume":
        ts = _parse_event_time(payload)
        await _handle_sleep_resume(ts)


async def _flush_sensor_buffer():
    """버퍼에 모인 센서 데이터를 DB에 저장 후 초기화"""
    data = dict(_sensor_buffer)
    _sensor_buffer.clear()
    try:
        await _save_sensor_data(data)
    except Exception as e:
        logger.error(f"센서 데이터 저장 실패: {e}")


def _parse_event_time(payload) -> datetime | None:
    """이벤트 페이로드에서 timestamp 파싱"""
    if isinstance(payload, dict):
        ts_str = payload.get("timestamp")
        if ts_str:
            try:
                return datetime.fromisoformat(ts_str)
            except ValueError:
                pass
    return None


# --------------------------------------------------
# MQTT 클라이언트 시작 / 종료
# --------------------------------------------------

_mqtt_client: mqtt.Client | None = None


def start_mqtt(loop: asyncio.AbstractEventLoop):
    """FastAPI 시작 시 호출 - MQTT 클라이언트 초기화 및 연결"""
    global _mqtt_client, _loop
    _loop = loop

    client = mqtt.Client(client_id="sleepingcare-backend")
    client.on_connect = _on_connect
    client.on_message = _on_message

    try:
        client.connect(
            settings.mqtt_broker_host,
            settings.mqtt_broker_port,
            keepalive=60,
        )
        client.loop_start()
        _mqtt_client = client
        logger.info(
            f"MQTT 연결 시도: {settings.mqtt_broker_host}:{settings.mqtt_broker_port}"
        )
    except Exception as e:
        logger.warning(f"MQTT 연결 실패 (서버는 계속 실행): {e}")


def stop_mqtt():
    """FastAPI 종료 시 호출"""
    global _mqtt_client
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        _mqtt_client = None
        logger.info("MQTT 연결 종료")


def is_mqtt_connected() -> bool:
    return _mqtt_client is not None and _mqtt_client.is_connected()
