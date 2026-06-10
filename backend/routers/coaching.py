"""
routers/coaching.py
POST /api/coaching/generate  - AI 코칭 생성
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from datetime import datetime, timezone, timedelta
from fastapi import Query
from core.database import get_conn
from models.schemas import CoachingGenerateIn, CoachingOut, RangeCoachingGenerateIn, RangeCoachingOut
from services.claude_coaching import generate_coaching, generate_range_coaching

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=CoachingOut)
async def create_coaching(
    body: CoachingGenerateIn,
    conn: Connection = Depends(get_conn),
):
    """
    POST /api/coaching/generate
    수면 세션 ID를 받아 Claude AI 코칭 생성 → DB 저장
    이미 코칭이 있는 경우 덮어쓰기
    """
    # 세션 존재 확인
    session = await conn.fetchrow(
        """
        SELECT id, duration_min, motion_count, regularity_diff_min,
               avg_temperature, avg_humidity, avg_light, avg_sound,
               env_score, pattern_score, total_score
        FROM sleep_sessions
        WHERE id = $1
        """,
        body.session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="수면 세션을 찾을 수 없어요")

    session_dict = dict(session)

    # Claude API 호출
    try:
        coaching_text = await generate_coaching(session_dict)
    except Exception as e:
        logger.error(f"Claude API 오류: {e}")
        raise HTTPException(status_code=502, detail=f"AI 코칭 생성 실패: {str(e)}")

    # 기존 코칭 삭제 후 새로 저장 (재생성 지원)
    await conn.execute(
        "DELETE FROM coaching_results WHERE session_id = $1",
        body.session_id,
    )

    row = await conn.fetchrow(
        """
        INSERT INTO coaching_results
            (session_id, good_points, bad_points, weekly_goal)
        VALUES
            ($1, $2, $3, $4)
        RETURNING id, session_id, good_points, bad_points, weekly_goal, created_at
        """,
        body.session_id,
        coaching_text["good_points"],
        coaching_text["bad_points"],
        coaching_text["weekly_goal"],
    )

    return CoachingOut(
        id=row["id"],
        session_id=row["session_id"],
        good_points=row["good_points"],
        bad_points=row["bad_points"],
        weekly_goal=row["weekly_goal"],
        created_at=row["created_at"],
    )


@router.get("/range", response_model=RangeCoachingOut | None)
async def get_range_coaching(
    range: str = Query(..., pattern="^(day|week|month)$"),
    conn: Connection = Depends(get_conn),
):
    """GET /api/coaching/range?range=day|week|month — 저장된 범위 코칭 조회"""
    row = await conn.fetchrow(
        "SELECT * FROM range_coaching_results WHERE range = $1 ORDER BY created_at DESC LIMIT 1",
        range,
    )
    if not row:
        return None
    return RangeCoachingOut(
        id=row["id"], range=row["range"],
        good_points=row["good_points"], bad_points=row["bad_points"],
        weekly_goal=row["weekly_goal"], created_at=row["created_at"],
    )


@router.post("/range/generate", response_model=RangeCoachingOut)
async def create_range_coaching(
    body: RangeCoachingGenerateIn,
    conn: Connection = Depends(get_conn),
):
    """POST /api/coaching/range/generate — 범위 기반 AI 코칭 생성"""
    days = {"day": 1, "week": 7, "month": 30}[body.range]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = await conn.fetch(
        """
        SELECT duration_min, motion_count, regularity_diff_min,
               avg_temperature, avg_humidity, avg_light, avg_sound,
               env_score, pattern_score, total_score
        FROM sleep_sessions
        WHERE start_time >= $1 AND end_time IS NOT NULL
        ORDER BY start_time DESC
        """,
        since,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 기간에 수면 데이터가 없어요")

    sessions = [dict(r) for r in rows]

    try:
        coaching_text = await generate_range_coaching(sessions, body.range)
    except Exception as e:
        logger.error(f"Claude API 오류: {e}")
        raise HTTPException(status_code=502, detail=f"AI 코칭 생성 실패: {str(e)}")

    await conn.execute(
        "DELETE FROM range_coaching_results WHERE range = $1",
        body.range,
    )

    row = await conn.fetchrow(
        """
        INSERT INTO range_coaching_results (range, good_points, bad_points, weekly_goal)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        body.range,
        coaching_text["good_points"],
        coaching_text["bad_points"],
        coaching_text["weekly_goal"],
    )

    return RangeCoachingOut(
        id=row["id"], range=row["range"],
        good_points=row["good_points"], bad_points=row["bad_points"],
        weekly_goal=row["weekly_goal"], created_at=row["created_at"],
        session_count=len(sessions),
    )
