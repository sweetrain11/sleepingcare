"""
sleep_score.py
수면 점수 계산 서비스

환경 점수 (40점)
├── 온도  (10점): 18~22°C 만점, 1°C 벗어날 때마다 2점 감점
├── 습도  (10점): 40~60% 만점, 5% 벗어날 때마다 2점 감점
├── 조도  (10점): 100 이하 만점, 초과 시 선형 감점
└── 소음  (10점): 300 이하 만점, 초과 시 선형 감점

패턴 점수 (60점)
├── 수면 시간 (20점): 7~9시간 만점, 1시간 벗어날 때마다 5점 감점
├── 규칙성   (20점): 편차 0분 만점, 30분마다 5점 감점
└── 뒤척임   (20점): 0회 만점, 5회마다 5점 감점
"""


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """값을 min~max 범위로 제한"""
    return max(min_val, min(max_val, value))


# --------------------------------------------------
# 환경 점수 계산 (각 10점 만점)
# --------------------------------------------------

def score_temperature(temp: float | None) -> int:
    """온도 점수: 18~22°C 만점, 1°C 벗어날 때마다 2점 감점"""
    if temp is None:
        return 5  # 센서 누락 시 부분 점수
    if 18 <= temp <= 22:
        return 10
    deviation = min(abs(temp - 18), abs(temp - 22)) if temp < 18 or temp > 22 else 0
    if temp < 18:
        deviation = 18 - temp
    else:
        deviation = temp - 22
    deduction = int(deviation) * 2
    return int(_clamp(10 - deduction, 0, 10))


def score_humidity(humidity: float | None) -> int:
    """습도 점수: 40~60% 만점, 5% 벗어날 때마다 2점 감점"""
    if humidity is None:
        return 5
    if 40 <= humidity <= 60:
        return 10
    if humidity < 40:
        deviation = 40 - humidity
    else:
        deviation = humidity - 60
    deduction = int(deviation / 5) * 2
    return int(_clamp(10 - deduction, 0, 10))


def score_light(light: float | None) -> int:
    """조도 점수: 100 이하 만점, 초과 시 선형 감점 (923 초과 시 0점)"""
    if light is None:
        return 5
    if light <= 100:
        return 10
    # 100~1023 범위에서 선형 감점
    excess = light - 100
    deduction = (excess / 923) * 10
    return int(_clamp(10 - deduction, 0, 10))


def score_sound(sound: float | None) -> int:
    """소음 점수: 300 이하 만점, 초과 시 선형 감점 (1023 초과 시 0점)"""
    if sound is None:
        return 5
    if sound <= 300:
        return 10
    excess = sound - 300
    deduction = (excess / 723) * 10
    return int(_clamp(10 - deduction, 0, 10))


def calc_env_score(
    avg_temperature: float | None,
    avg_humidity: float | None,
    avg_light: float | None,
    avg_sound: float | None,
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
    """수면 시간 점수: 7~9시간(420~540분) 만점, 1시간 벗어날 때마다 5점 감점"""
    if duration_min is None:
        return 10
    if 420 <= duration_min <= 540:
        return 20
    if duration_min < 420:
        deviation_hours = (420 - duration_min) / 60
    else:
        deviation_hours = (duration_min - 540) / 60
    deduction = int(deviation_hours) * 5
    return int(_clamp(20 - deduction, 0, 20))


def score_regularity(regularity_diff_min: int | None) -> int:
    """규칙성 점수: 편차 0분 만점, 30분마다 5점 감점"""
    if regularity_diff_min is None:
        return 10  # 첫 세션은 비교 불가 → 부분 점수
    deduction = (abs(regularity_diff_min) // 30) * 5
    return int(_clamp(20 - deduction, 0, 20))


def score_motion(motion_count: int) -> int:
    """뒤척임 점수: 0회 만점, 5회마다 5점 감점"""
    deduction = (motion_count // 5) * 5
    return int(_clamp(20 - deduction, 0, 20))


def calc_pattern_score(
    duration_min: int | None,
    regularity_diff_min: int | None,
    motion_count: int,
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
    avg_temperature: float | None,
    avg_humidity: float | None,
    avg_light: float | None,
    avg_sound: float | None,
    duration_min: int | None,
    regularity_diff_min: int | None,
    motion_count: int,
) -> tuple[int, int, int]:
    """
    종합 점수 계산
    Returns: (env_score, pattern_score, total_score)
    """
    env = calc_env_score(avg_temperature, avg_humidity, avg_light, avg_sound)
    pattern = calc_pattern_score(duration_min, regularity_diff_min, motion_count)
    return env, pattern, env + pattern
