"""
sleep_score.py
수면 점수 계산 서비스

환경 점수 (40점)
├── 온도  (10점): 16~20°C 만점, 비선형 구간 감점
├── 습도  (10점): 40~60% 만점, 5%마다 2점 감점
├── 조도  (10점): 0~5 lux 만점, 구간별 감점 (lux 단위)
└── 소음  (10점): 30dB 미만 만점, 구간별 감점 (dB 단위)

패턴 점수 (60점)
├── 수면 시간 (20점): 7~9시간 만점, 1시간마다 5점 감점
├── 규칙성   (20점): 편차 0분 만점, 30분마다 5점 감점
└── 뒤척임   (20점): 0회 만점, 5회마다 5점 감점

근거:
- 온도: SLEEP 저널 34,096명 실증 연구 (18~20°C 최적) + NSF 권고 (15~19°C)
         5°C 초과 시 수면 효율 5~10% 임상적 저하 (Harvard Marcus Institute, PubMed)
- 습도: ASHRAE Standard 55 + Sleep Foundation (40~60% RH)
- 조도: 멜라토닌 억제 연구 기반 lux 단위 기준
- 소음: WHO 커뮤니티 소음 가이드라인 (침실 30dB 미만 권고)
- 수면 시간: AASM·수면연구학회 공동 합의문 (7시간 이상), NSF (7~9시간)
- 규칙성: UK Biobank 60,977명 연구 + NSF 전문가 패널 합의 (63편 논문 검토)
- 뒤척임: 액티그래피 기반 수면 연구 (운동 활동 = 수면 질 지표)
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
    만점 구간: 16~20°C
    비선형 구간 감점 — 5°C 초과 시 수면 효율 임상적 저하 연구 반영

    16~20°C              → 10점
    15~16°C / 20~21°C    →  9점
    13~15°C / 21~23°C    →  6점
    23~25°C              →  3점  (warm side만 해당, cold side는 13°C 미만 시 바로 0점)
    13°C 미만 / 25°C 초과 →  0점
    """
    if temp is None:
        return 5  # 센서 누락 시 부분 점수

    if 16 <= temp <= 20:
        return 10
    if 15 <= temp < 16 or 20 < temp <= 21:
        return 9
    if 13 <= temp < 15 or 21 < temp <= 23:
        return 6
    if 23 < temp <= 25:
        return 3
    return 0


def score_humidity(humidity: float | None) -> int:
    """
    습도 점수
    만점 구간: 40~60% RH
    5%마다 2점 감점
    """
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


def score_light(lux: float | None) -> int:
    """
    조도 점수 (lux 단위)
    멜라토닌 억제 연구 기반 구간 설정
    근사 변환 오차를 고려해 구간을 넓게 설정

    0~5 lux      → 10점 (완전 암실~매우 어두움)
    5~30 lux     →  6점 (희미한 빛)
    30~100 lux   →  3점 (실내 간접 조명 수준)
    100 lux 초과 →  0점
    """
    if lux is None:
        return 5
    if lux <= 5:
        return 10
    if lux <= 30:
        return 6
    if lux <= 100:
        return 3
    return 0


def score_sound(db: float | None) -> int:
    """
    소음 점수 (dB 단위)
    WHO 커뮤니티 소음 가이드라인 기반 구간 설정
    근사 변환 오차를 고려해 구간을 넓게 설정

    30dB 미만    → 10점 (WHO 침실 권고 이하)
    30~45dB      →  6점 (WHO 야간 외부 권고 이하)
    45~65dB      →  3점 (일상 소음 수준)
    65dB 초과    →  0점
    """
    if db is None:
        return 5
    if db < 30:
        return 10
    if db < 45:
        return 6
    if db < 65:
        return 3
    return 0


def calc_env_score(
    avg_temperature: float | None,
    avg_humidity:    float | None,
    avg_light:       float | None,  # lux 단위
    avg_sound:       float | None,  # dB 단위
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
    만점 구간: 7~9시간 (420~540분)
    1시간 벗어날 때마다 5점 감점
    근거: AASM·수면연구학회 공동 합의문, NSF 권고 (7~9시간)
    """
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
    """
    규칙성 점수
    편차 0분 만점, 30분마다 5점 감점
    근거: UK Biobank 60,977명 연구 + NSF 전문가 패널 합의
    감점 간격(30분)은 설계 선택
    """
    if regularity_diff_min is None:
        return 10  # 첫 세션은 비교 불가 → 부분 점수
    deduction = (abs(regularity_diff_min) // 30) * 5
    return int(_clamp(20 - deduction, 0, 20))


def score_motion(motion_count: int) -> int:
    """
    뒤척임 점수
    0회 만점, 5회마다 5점 감점
    근거: 액티그래피 기반 수면 연구 (운동 활동 = 수면 질 지표)
    감점 간격(5회)은 PIR 센서 감도에 의존하는 설계 선택
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
    avg_light:           float | None,  # lux 단위
    avg_sound:           float | None,  # dB 단위
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