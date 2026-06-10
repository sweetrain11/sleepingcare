"""
services/sleep_session.py
수면 세션 종료 처리: 센서 집계 → 규칙성 계산 → 점수 산출 → DB 업데이트
"""
from datetime import datetime

from services.sleep_score import calc_total_score

MIN_SLEEP_MINUTES = 5   # 이 미만 세션은 오기록으로 간주 → 삭제


async def finalize_sleep_session(conn, ts: datetime) -> tuple[int, int] | tuple[None, str] | None:
    """
    수면 세션 종료 처리.
    Returns:
        (session_id, total_score)  정상 종료
        (None, "too_short")        5분 미만 → 세션 삭제
        None                       활성 세션 없음
    """
    session = await conn.fetchrow(
        "SELECT id, start_time FROM sleep_sessions WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
    )
    if not session:
        return None

    session_id = session["id"]
    start_time = session["start_time"]
    duration_min = int((ts - start_time).total_seconds() / 60)

    # 5분 미만: 오기록으로 간주 → 세션 삭제
    if duration_min < MIN_SLEEP_MINUTES:
        await conn.execute("DELETE FROM sleep_sessions WHERE id = $1", session_id)
        return None, "too_short"

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

    # 규칙성: 직전 세션과 취침 시각 비교 (원형 거리)
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
        diff = abs(
            (start_time.hour * 60 + start_time.minute)
            - (prev_start.hour * 60 + prev_start.minute)
        )
        regularity_diff = int(min(diff, 1440 - diff))

    env_score, pattern_score, total_score = calc_total_score(
        avg_temp, avg_hum, avg_light, avg_sound,
        duration_min, regularity_diff, motion_cnt,
    )

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

    return session_id, total_score
