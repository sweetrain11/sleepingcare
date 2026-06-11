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
from services.sleep_session import finalize_sleep_session
from routers.sensors import broadcast_sensor, broadcast_sleep_state

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
    await broadcast_sleep_state(is_sleeping=True, session_id=session_id, start_time=ts)
    logger.info(f"수면 세션 시작: id={session_id}, start_time={ts}")


async def _handle_sleep_end(timestamp: datetime | None):
    """수면 종료 이벤트 → 세션 집계/점수 계산을 서비스에 위임"""
    ts = timestamp or datetime.now(timezone.utc)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await finalize_sleep_session(conn, ts)
    if result is None:
        logger.warning("종료할 수면 세션 없음")
    else:
        session_id, payload = result
        if payload == "too_short":
            await broadcast_sleep_state(is_sleeping=False)
            logger.info("수면 세션 삭제: 5분 미만 오기록")
        else:
            await broadcast_sleep_state(is_sleeping=False, session_id=session_id)
            logger.info(f"수면 세션 종료: id={session_id}, total={payload}점")


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
                avg_temperature = NULL, avg_humidity = NULL,
                avg_light = NULL, avg_sound = NULL,
                motion_count = NULL, regularity_diff_min = NULL,
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
            try:
                _sensor_buffer["arduino_time"] = datetime.fromisoformat(str(payload))
            except (ValueError, TypeError):
                _sensor_buffer["arduino_time"] = None
            await _flush_sensor_buffer()
        else:
            if sensor_key == "motion":
                if isinstance(payload, str):
                    _sensor_buffer[sensor_key] = payload.lower() not in ("false", "0", "")
                else:
                    _sensor_buffer[sensor_key] = bool(payload)
            elif sensor_key in ("light", "sound"):
                _sensor_buffer[sensor_key] = float(payload) if payload is not None else None
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
    """버퍼에 모인 센서 데이터를 DB에 저장 후 WebSocket 브로드캐스트"""
    data = dict(_sensor_buffer)
    _sensor_buffer.clear()
    try:
        await _save_sensor_data(data)
    except Exception as e:
        logger.error(f"센서 데이터 저장 실패: {e}")
        return

    try:
        arduino_time = data.get("arduino_time")
        await broadcast_sensor({
            "time":         datetime.now(timezone.utc).isoformat(),
            "arduino_time": arduino_time.isoformat() if isinstance(arduino_time, datetime) else arduino_time,
            "temperature":  data.get("temperature"),
            "humidity":     data.get("humidity"),
            "light":        data.get("light"),
            "sound":        data.get("sound"),
            "motion":       data.get("motion"),
        })
    except Exception as e:
        logger.error(f"WebSocket 브로드캐스트 실패: {e}")


def _parse_event_time(payload) -> datetime | None:
    """이벤트 페이로드에서 timestamp 파싱 (문자열 또는 dict 모두 처리)"""
    try:
        if isinstance(payload, str):
            return datetime.fromisoformat(payload)
        if isinstance(payload, dict):
            ts_str = payload.get("timestamp")
            if ts_str:
                return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
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
