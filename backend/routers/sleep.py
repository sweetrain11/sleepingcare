"""
routers/sleep.py
GET  /api/sleep/status             - 현재 수면 상태 조회
POST /api/sleep/start              - 수면 수동 시작
POST /api/sleep/end                - 수면 수동 종료
GET  /api/sleep/score/{session_id} - 수면 세션 점수 조회
GET  /api/sleep/history            - 수면 이력 조회 (week | month)
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Connection

from core.database import get_conn
from models.schemas import SleepScoreOut, SleepHistoryOut, CoachingOut, SleepStatusOut, SleepControlOut
from services.sleep_session import finalize_sleep_session
from routers.sensors import broadcast_sleep_state

router = APIRouter()


def _row_to_score(row) -> SleepScoreOut:
    """asyncpg Record → SleepScoreOut 변환"""
    coaching = None
    if row.get("coaching_id"):
        coaching = CoachingOut(
            id=row["coaching_id"],
            session_id=row["id"],
            good_points=row.get("good_points"),
            bad_points=row.get("bad_points"),
            weekly_goal=row.get("weekly_goal"),
            created_at=row["coaching_created_at"],
        )

    return SleepScoreOut(
        session_id=row["id"],
        start_time=row["start_time"],
        end_time=row.get("end_time"),
        duration_min=row.get("duration_min"),
        avg_temperature=row.get("avg_temperature"),
        avg_humidity=row.get("avg_humidity"),
        avg_light=row.get("avg_light"),
        avg_sound=row.get("avg_sound"),
        motion_count=row.get("motion_count") or 0,
        regularity_diff_min=row.get("regularity_diff_min"),
        env_score=row.get("env_score"),
        pattern_score=row.get("pattern_score"),
        total_score=row.get("total_score"),
        coaching=coaching,
    )


# 세션 + 코칭 JOIN 쿼리
_SESSION_QUERY = """
    SELECT
        s.id, s.start_time, s.end_time, s.duration_min,
        s.avg_temperature, s.avg_humidity, s.avg_light, s.avg_sound,
        s.motion_count, s.regularity_diff_min,
        s.env_score, s.pattern_score, s.total_score,
        c.id          AS coaching_id,
        c.good_points, c.bad_points, c.weekly_goal,
        c.created_at  AS coaching_created_at
    FROM sleep_sessions s
    LEFT JOIN coaching_results c ON c.session_id = s.id
"""


@router.get("/status", response_model=SleepStatusOut)
async def get_sleep_status(conn: Connection = Depends(get_conn)):
    """
    GET /api/sleep/status
    현재 수면 중 여부 조회 (end_time이 NULL인 세션 존재 여부)
    """
    row = await conn.fetchrow(
        "SELECT id, start_time FROM sleep_sessions WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
    )
    if row:
        return SleepStatusOut(is_sleeping=True, session_id=row["id"], start_time=row["start_time"])
    return SleepStatusOut(is_sleeping=False)


@router.post("/start", response_model=SleepControlOut)
async def manual_sleep_start(conn: Connection = Depends(get_conn)):
    """
    POST /api/sleep/start
    수면 수동 시작 - 이미 진행 중인 세션이 없을 때만 생성
    """
    # 활성 세션 중복 확인
    active = await conn.fetchrow(
        "SELECT id FROM sleep_sessions WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
    )
    if active:
        return SleepControlOut(
            success=False,
            message="이미 수면 세션이 진행 중이에요",
            session_id=active["id"],
        )

    now = datetime.now(timezone.utc)
    session_id = await conn.fetchval(
        "INSERT INTO sleep_sessions (start_time) VALUES ($1) RETURNING id",
        now,
    )
    await broadcast_sleep_state(is_sleeping=True, session_id=session_id, start_time=now)
    return SleepControlOut(success=True, message="수면 시작", session_id=session_id)


@router.post("/end", response_model=SleepControlOut)
async def manual_sleep_end(conn: Connection = Depends(get_conn)):
    """
    POST /api/sleep/end
    수면 수동 종료 - 활성 세션을 집계하고 점수 계산
    """
    now = datetime.now(timezone.utc)
    result = await finalize_sleep_session(conn, now)
    if result is None:
        return SleepControlOut(success=False, message="종료할 수면 세션이 없어요")
    session_id, payload = result
    if payload == "too_short":
        await broadcast_sleep_state(is_sleeping=False)
        return SleepControlOut(success=False, message="수면 시간이 너무 짧아요 (5분 미만은 기록되지 않아요)")
    await broadcast_sleep_state(is_sleeping=False, session_id=session_id)
    return SleepControlOut(success=True, message=f"수면 종료 (점수: {payload}점)", session_id=session_id)


@router.get("/score/{session_id}", response_model=SleepScoreOut)
async def get_sleep_score(
    session_id: int,
    conn: Connection = Depends(get_conn),
):
    """
    GET /api/sleep/score/{session_id}
    특정 수면 세션의 점수 + 코칭 결과 조회
    """
    row = await conn.fetchrow(
        _SESSION_QUERY + " WHERE s.id = $1",
        session_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="수면 세션을 찾을 수 없어요")

    return _row_to_score(row)


@router.get("/history", response_model=SleepHistoryOut)
async def get_sleep_history(
    range: str = Query("week", pattern="^(day|week|month)$"),
    conn: Connection = Depends(get_conn),
):
    """
    GET /api/sleep/history?range=day|week|month
    day:   가장 최근 완료된 세션 1개
    week:  최근 7일 이력
    month: 최근 30일 이력
    """
    if range == "day":
        rows = await conn.fetch(
            _SESSION_QUERY + " WHERE s.end_time IS NOT NULL ORDER BY s.start_time DESC LIMIT 1"
        )
    else:
        days = 7 if range == "week" else 30
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = await conn.fetch(
            _SESSION_QUERY + " WHERE s.start_time >= $1 ORDER BY s.start_time DESC",
            since,
        )

    return SleepHistoryOut(
        range=range,
        sessions=[_row_to_score(r) for r in rows],
    )
