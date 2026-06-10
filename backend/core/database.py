import asyncpg
from core.config import settings

# 전역 커넥션 풀
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """커넥션 풀 반환 (없으면 생성)"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            timeout=30,
            max_inactive_connection_lifetime=300,
        )
        await _migrate(_pool)
    return _pool


async def _migrate(pool: asyncpg.Pool):
    """앱 시작 시 누락된 테이블/컬럼 자동 생성"""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS range_coaching_results (
                id          SERIAL      PRIMARY KEY,
                range       VARCHAR(10) NOT NULL,
                good_points TEXT,
                bad_points  TEXT,
                weekly_goal TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


async def close_pool():
    """앱 종료 시 커넥션 풀 닫기"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_conn():
    """라우터에서 사용할 DB 커넥션 의존성"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
