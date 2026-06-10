"""
scripts/clean_short_sessions.py
5분 미만 잘못 기록된 수면 세션 삭제

실행:
    cd backend
    python scripts/clean_short_sessions.py
"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:password@172.18.55.21:5432/sleepingcare_db?sslmode=disable"


async def clean():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, start_time, end_time, duration_min, total_score
            FROM sleep_sessions
            WHERE duration_min IS NULL
               OR duration_min < 5
               OR (start_time >= '2026-05-27 00:00:00+00'
                   AND start_time < '2026-05-28 00:00:00+00')
            ORDER BY start_time DESC
            """
        )

        if not rows:
            print("삭제할 세션이 없어요.")
            return

        print(f"삭제 대상 {len(rows)}개:")
        for r in rows:
            print(f"  id={r['id']} | {r['start_time']} | {r['duration_min']}분 | {r['total_score']}점")

        await conn.execute(
            """
            DELETE FROM sleep_sessions
            WHERE duration_min IS NULL
               OR duration_min < 5
               OR (start_time >= '2026-05-27 00:00:00+00'
                   AND start_time < '2026-05-28 00:00:00+00')
            """
        )
        print(f"\n✅ {len(rows)}개 세션 삭제 완료")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(clean())
