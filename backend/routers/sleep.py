"""
routers/sleep.py
GET /api/sleep/score/{session_id}  - 수면 세션 점수 조회
GET /api/sleep/history             - 수면 이력 조회 (week | month)
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Connection

from core.database import get_conn
from models.schemas import SleepScoreOut, SleepHistoryOut, CoachingOut

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
    range: str = Query("week", pattern="^(week|month)$"),
    conn: Connection = Depends(get_conn),
):
    """
    GET /api/sleep/history?range=week|month
    주간(7일) 또는 월간(30일) 수면 이력 조회
    최신순 정렬
    """
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
