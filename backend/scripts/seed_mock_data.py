"""
scripts/seed_mock_data.py
가상 인물 A (이수면, 28세 직장인) 7일치 목업 수면 데이터 삽입

실행:
    cd backend
    python scripts/seed_mock_data.py

캐릭터 설정:
    - 취침 자정 전후, 기상 7~8시대
    - 여름 더위로 실내 22~24°C (약간 높음)
    - 주중 규칙적, 주말에 늦게 자는 패턴
    - 조도 낮음 (암실), 소음 양호

7일 수면 이야기:
    5/21(수): 첫날, 평범한 수면 (82점)
    5/22(목): 늦게 자서 수면 부족 (72점)
    5/23(금): 회복, 숙면 (83점)
    5/24(토): 주말, 늦잠 + 더위/소음 (72점)
    5/25(일): 스케줄 복귀 시도 (86점)
    5/26(월): 규칙성 개선 (87점)
    5/27(화): 최고의 수면, 완벽한 규칙성 (96점)
"""

import asyncio
import asyncpg
from datetime import datetime, timezone

DATABASE_URL = "postgresql://postgres:password@172.18.55.21:5432/sleepingcare_db?sslmode=disable"


def ts(s):
    """'2026-05-21 14:45:00+00' 문자열 → timezone-aware datetime 객체"""
    return datetime.fromisoformat(s.replace("+00", "+00:00"))

# --------------------------------------------------
# 목업 데이터 (모든 시각은 UTC)
# KST = UTC+9 이므로 KST 시각에서 -9시간
# --------------------------------------------------
SESSIONS = [
    {
        # 5/21(수) 23:45 KST → 5/22(목) 07:15 KST
        "start_time":           "2026-05-21 14:45:00+00",
        "end_time":             "2026-05-21 22:15:00+00",
        "duration_min":         450,    # 7h 30m
        "avg_temperature":      22.5,
        "avg_humidity":         55.0,
        "avg_light":            2.1,    # lux
        "avg_sound":            32.0,   # dB
        "motion_count":         3,
        "regularity_diff_min":  None,   # 첫 세션 → 비교 없음
        "env_score":            32,     # 온도6 습도10 조도10 소음6
        "pattern_score":        50,     # 수면시간20 규칙성10(없음→부분) 뒤척임20
        "total_score":          82,
    },
    {
        # 5/23(금) 01:20 KST → 07:50 KST (늦게 잠)
        "start_time":           "2026-05-22 16:20:00+00",
        "end_time":             "2026-05-22 22:50:00+00",
        "duration_min":         390,    # 6h 30m
        "avg_temperature":      23.0,
        "avg_humidity":         57.0,
        "avg_light":            1.8,
        "avg_sound":            35.0,
        "motion_count":         5,
        "regularity_diff_min":  95,     # 전날 23:45 → 01:20, 편차 95분
        "env_score":            32,     # 온도6 습도10 조도10 소음6
        "pattern_score":        40,     # 수면시간20 규칙성5(95분 편차) 뒤척임15
        "total_score":          72,
    },
    {
        # 5/24(토) 00:10 KST → 08:00 KST
        "start_time":           "2026-05-23 15:10:00+00",
        "end_time":             "2026-05-23 23:00:00+00",
        "duration_min":         470,    # 7h 50m
        "avg_temperature":      23.5,
        "avg_humidity":         62.0,
        "avg_light":            1.5,
        "avg_sound":            28.0,
        "motion_count":         2,
        "regularity_diff_min":  70,     # 01:20 → 00:10, 편차 70분
        "env_score":            33,     # 온도3 습도10 조도10 소음10
        "pattern_score":        50,     # 수면시간20 규칙성10(70분) 뒤척임20
        "total_score":          83,
    },
    {
        # 5/25(일) 01:30 KST → 09:30 KST (주말 늦잠)
        "start_time":           "2026-05-24 16:30:00+00",
        "end_time":             "2026-05-25 00:30:00+00",
        "duration_min":         480,    # 8h
        "avg_temperature":      24.0,
        "avg_humidity":         65.0,
        "avg_light":            2.3,
        "avg_sound":            42.0,   # 이웃 소음
        "motion_count":         8,      # 더위+소음으로 뒤척임
        "regularity_diff_min":  80,     # 00:10 → 01:30, 편차 80분
        "env_score":            27,     # 온도3 습도8 조도10 소음6
        "pattern_score":        45,     # 수면시간20 규칙성10(80분) 뒤척임15
        "total_score":          72,
    },
    {
        # 5/26(월) 00:30 KST → 08:00 KST (복귀 시도)
        "start_time":           "2026-05-25 15:30:00+00",
        "end_time":             "2026-05-25 23:00:00+00",
        "duration_min":         450,    # 7h 30m
        "avg_temperature":      23.0,
        "avg_humidity":         58.0,
        "avg_light":            1.2,
        "avg_sound":            29.5,
        "motion_count":         4,
        "regularity_diff_min":  60,     # 01:30 → 00:30, 편차 60분
        "env_score":            36,     # 온도6 습도10 조도10 소음10
        "pattern_score":        50,     # 수면시간20 규칙성10(60분) 뒤척임20
        "total_score":          86,
    },
    {
        # 5/26(월) 23:50 KST → 5/27(화) 07:20 KST
        "start_time":           "2026-05-26 14:50:00+00",
        "end_time":             "2026-05-26 22:20:00+00",
        "duration_min":         450,    # 7h 30m
        "avg_temperature":      22.0,
        "avg_humidity":         52.0,
        "avg_light":            1.8,
        "avg_sound":            31.0,
        "motion_count":         2,
        "regularity_diff_min":  40,     # 00:30 → 23:50, 편차 40분
        "env_score":            32,     # 온도6 습도10 조도10 소음6
        "pattern_score":        55,     # 수면시간20 규칙성15(40분) 뒤척임20
        "total_score":          87,
    },
    {
        # 5/27(화) 23:40 KST → 5/28(수) 07:10 KST
        "start_time":           "2026-05-27 14:40:00+00",
        "end_time":             "2026-05-27 22:10:00+00",
        "duration_min":         450,    # 7h 30m
        "avg_temperature":      21.5,
        "avg_humidity":         50.0,
        "avg_light":            1.5,
        "avg_sound":            29.0,
        "motion_count":         3,
        "regularity_diff_min":  10,     # 23:50 → 23:40, 편차 10분
        "env_score":            36,     # 온도6 습도10 조도10 소음10
        "pattern_score":        60,     # 수면시간20 규칙성20(10분) 뒤척임20
        "total_score":          96,
    },
]


async def seed():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 기존 목업 데이터 있으면 확인
        count = await conn.fetchval("SELECT COUNT(*) FROM sleep_sessions")
        if count > 0:
            print(f"⚠️  sleep_sessions에 이미 {count}개 세션이 있어요.")
            print("   기존 데이터를 유지하고 추가로 삽입할게요.\n")

        inserted = 0
        for i, s in enumerate(SESSIONS, 1):
            await conn.execute(
                """
                INSERT INTO sleep_sessions
                    (start_time, end_time, duration_min,
                     avg_temperature, avg_humidity, avg_light, avg_sound,
                     motion_count, regularity_diff_min,
                     env_score, pattern_score, total_score)
                VALUES
                    ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                ts(s["start_time"]), ts(s["end_time"]), s["duration_min"],
                s["avg_temperature"], s["avg_humidity"],
                s["avg_light"], s["avg_sound"],
                s["motion_count"], s["regularity_diff_min"],
                s["env_score"], s["pattern_score"], s["total_score"],
            )
            print(f"  ✅ Day {i}: {s['start_time'][:10]} KST → {s['total_score']}점 "
                  f"(환경 {s['env_score']} / 패턴 {s['pattern_score']})")
            inserted += 1

        print(f"\n총 {inserted}개 세션 삽입 완료!")
        print("리포트 페이지를 새로고침하면 데이터가 보여요.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
