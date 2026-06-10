"""
sleep_score.py
수면 점수 계산 서비스

환경 점수 (40점)
├── 온도  (10점): 15~19°C 만점, 구간별 감점
├── 습도  (10점): 40~60% 만점, 구간별 감점
├── 조도  (10점): 0~5 lux 만점, 구간별 감점
└── 소음  (10점): 30dB 미만 만점, 구간별 감점

패턴 점수 (60점)
├── 수면 시간 (20점): 7~9시간 만점, 구간별 감점
├── 규칙성   (20점): 편차 0~29분 만점, 30분마다 5점 감점
└── 뒤척임   (20점): 0~4회 만점, 5회마다 5점 감점

근거:
- 온도: NSF / Cleveland Clinic (Drerup M.) — 최적 15~19°C (60~67°F)
- 습도: ASHRAE Standard 55-2020 / Sekhar et al. 2020 — 40~60% RH
- 조도: Sleep Foundation (NSF 산하) — 10 lux 이상 수면 질 저하
- 소음: WHO Community Noise Guidelines (1999) / WHO Night Noise Guidelines (2009) — 30 dB 미만
- 수면 시간: NSF (Hirshkowitz et al., Sleep Health, 2015) / AASM·SRS 공동 합의 — 7~9시간
- 규칙성: NSF Sleep Timing & Variability Panel (Sletten et al., Sleep Health, 2023)
- 뒤척임: PSQI (Buysse et al., 1989) / Actigraphy 기반 수면 연구
"""


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """값을 min~max 범위로 제한"""
    return max(min_val, min(max_val, value))


# --------------------------------------------------
# 환경 점수 계산 (각 10점 만점)
# --------------------------------------------------

def score_temperature(temp: float | None) -> int:
    """
    온도 점수 (°C 단위)
    만점 구간: 15~19°C (NSF / Cleveland Clinic 권장)

    15~19°C              → 10점
    13~15°C / 19~21°C    →  6점
    21~23°C              →  3점
    13°C 미만 / 23°C 초과 →  0점
    센서 누락             →  5점
    """
    if temp is None:
        return 5
    if 15 <= temp <= 19:
        return 10
    if 13 <= temp < 15 or 19 < temp <= 21:
        return 6
    if 21 < temp <= 23:
        return 3
    return 0


def score_humidity(humidity: float | None) -> int:
    """
    습도 점수 (% RH)
    만점 구간: 40~60% (ASHRAE Standard 55)

    40~60%           → 10점
    35~40% / 60~65%  →  6점
    30~35% / 65~70%  →  3점
    30% 미만 / 70% 초과 → 0점
    센서 누락          →  5점
    """
    if humidity is None:
        return 5
    if 40 <= humidity <= 60:
        return 10
    if 35 <= humidity < 40 or 60 < humidity <= 65:
        return 6
    if 30 <= humidity < 35 or 65 < humidity <= 70:
        return 3
    return 0


def score_light(lux: float | None) -> int:
    """
    조도 점수 (lux 단위)
    멜라토닌 억제 연구 기반 (Sleep Foundation)

    0~5 lux      → 10점
    5~10 lux     →  8점
    10~30 lux    →  5점
    30~100 lux   →  2점
    100 lux 초과 →  0점
    센서 누락     →  5점
    """
    if lux is None:
        return 5
    if lux <= 5:
        return 10
    if lux <= 10:
        return 8
    if lux <= 30:
        return 5
    if lux <= 100:
        return 2
    return 0


def score_sound(db: float | None) -> int:
    """
    소음 점수 (dB 단위)
    WHO 커뮤니티 소음 가이드라인 기반

    30 dB 미만   → 10점
    30~40 dB     →  7점
    40~55 dB     →  4점
    55~65 dB     →  1점
    65 dB 초과   →  0점
    센서 누락     →  5점
    """
    if db is None:
        return 5
    if db < 30:
        return 10
    if db < 40:
        return 7
    if db < 55:
        return 4
    if db < 65:
        return 1
    return 0


def calc_env_score(
    avg_temperature: float | None,
    avg_humidity:    float | None,
    avg_light:       float | None,
    avg_sound:       float | None,
) -> int:
    """환경 점수 합산 (40점 만점)"""
    return (
        score_temperature(avg_temperature)
        + score_humidity(avg_humidity)
        + score_light(avg_light)
        + score_sound(avg_sound)
    )


# --------------------------------------------------
# 패턴 점수 계산 (각 20점 만점)
# --------------------------------------------------

def score_duration(duration_min: int | None) -> int:
    """
    수면 시간 점수
    만점 구간: 7~9시간 (NSF / AASM·SRS 공동 합의)

    420~540분 (7~9h)   → 20점
    360~420 / 540~600분 → 15점
    300~360 / 600~660분 → 10점
    240~300 / 660분 초과 →  5점
    240분 미만           →  0점
    센서 누락            → 10점
    """
    if duration_min is None:
        return 10
    if 420 <= duration_min <= 540:
        return 20
    if 360 <= duration_min < 420 or 540 < duration_min <= 600:
        return 15
    if 300 <= duration_min < 360 or 600 < duration_min <= 660:
        return 10
    if 240 <= duration_min < 300 or duration_min > 660:
        return 5
    return 0


def score_regularity(regularity_diff_min: int | None) -> int:
    """
    규칙성 점수
    편차 0~29분 만점, 30분마다 5점 감점
    근거: NSF Sleep Timing & Variability Panel (Sletten et al., Sleep Health, 2023)

    0~29분   → 20점
    30~59분  → 15점
    60~89분  → 10점
    90~119분 →  5점
    120분 이상 → 0점
    첫 세션   → 10점
    """
    if regularity_diff_min is None:
        return 10
    deduction = (abs(regularity_diff_min) // 30) * 5
    return int(_clamp(20 - deduction, 0, 20))


def score_motion(motion_count: int) -> int:
    """
    뒤척임 점수
    0~4회 만점, 5회마다 5점 감점
    근거: PSQI (Buysse et al., 1989) / Actigraphy 기반 수면 연구

    0~4회   → 20점
    5~9회   → 15점
    10~14회 → 10점
    15~19회 →  5점
    20회 이상 → 0점
    """
    deduction = (motion_count // 5) * 5
    return int(_clamp(20 - deduction, 0, 20))


def calc_pattern_score(
    duration_min:        int | None,
    regularity_diff_min: int | None,
    motion_count:        int,
) -> int:
    """패턴 점수 합산 (60점 만점)"""
    return (
        score_duration(duration_min)
        + score_regularity(regularity_diff_min)
        + score_motion(motion_count)
    )


# --------------------------------------------------
# 종합 점수
# --------------------------------------------------

def calc_total_score(
    avg_temperature:     float | None,
    avg_humidity:        float | None,
    avg_light:           float | None,
    avg_sound:           float | None,
    duration_min:        int | None,
    regularity_diff_min: int | None,
    motion_count:        int,
) -> tuple[int, int, int]:
    """
    종합 점수 계산
    Returns: (env_score, pattern_score, total_score)
    """
    env     = calc_env_score(avg_temperature, avg_humidity, avg_light, avg_sound)
    pattern = calc_pattern_score(duration_min, regularity_diff_min, motion_count)
    return env, pattern, env + pattern
