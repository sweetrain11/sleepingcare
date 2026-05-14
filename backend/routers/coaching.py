"""
routers/coaching.py
POST /api/coaching/generate  - AI 코칭 생성
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from core.database import get_conn
from models.schemas import CoachingGenerateIn, CoachingOut
from services.claude_coaching import generate_coaching

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
