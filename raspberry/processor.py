# =============================================
# processor.py
# 전처리: 이동평균, 단위 변환, 타임존 추가, 수면 이벤트 감지
# =============================================

import time
import logging
import math
from collections import deque

logger = logging.getLogger(__name__)

# ---- 이동평균 설정 ----
MOVING_AVG_N = 5

# ---- 수면 이벤트 감지 설정 ----
SLEEP_LIGHT_THRESHOLD  = 100    # 수면 시작 조도 임계값 (원시값 0~1023 기준)
SLEEP_START_SECONDS    = 60     # 수면 시작 판단 유지 시간 (초)
WAKE_PIR_COUNT         = 3      # 수면 종료 판단 PIR 감지 횟수
WAKE_PIR_WINDOW        = 10     # 수면 종료 판단 시간 윈도우 (초)
RESUME_WINDOW          = 300    # 수면 재개 판단 시간 윈도우 (초, 5분)

# ---- 단위 변환 설정 ----
# [조도 변환: CDS 원시값 → lux 근사]
# GL5528 계열 등 일반 아두이노 호환 CDS 센서 기준 경험적 근사 공식
# 실제 센서 모델 및 회로 구성(저항값 등)에 따라 오차 발생 가능
# 정밀도가 필요한 경우 실측값으로 캘리브레이션 권장
#
# 공식 근거:
#   CDS 센서 저항은 조도에 반비례하므로 log 스케일 매핑 적용
#   원시값 0   ≈ 완전 암실 → ~0 lux
#   원시값 512 ≈ 실내 조명 → ~50~200 lux (회로 구성 의존)
#   원시값 1023 ≈ 직사광선 → ~10000 lux 이상
#   ADC 0~1023을 0.0~1.0으로 정규화 후 lux 범위(0~10000)로 log 스케일 매핑
LUX_MAX = 10000.0   # 센서 측정 가능 최대 lux 근사값

# [소음 변환: 사운드 센서 원시값 → dB 근사]
# 아두이노 호환 일반 사운드 센서(아날로그 출력) 기준 경험적 근사 공식
# 실제 센서 모델(KY-038 등) 및 마이크 감도에 따라 오차 발생 가능
# 정밀도가 필요한 경우 실측 환경에서 캘리브레이션 권장
#
# 공식 근거:
#   사운드 센서 아날로그 출력은 음압(amplitude)에 비례
#   dB는 음압의 log 스케일이므로: dB ≈ 20 * log10(amplitude / reference)
#   원시값 0    ≈ 무음 → ~30 dB (주변 소음 바닥값)
#   원시값 512  ≈ 보통 대화 → ~60 dB
#   원시값 1023 ≈ 매우 큰 소리 → ~90 dB
DB_MIN = 30.0   # 원시값 0에 대응하는 최소 dB (주변 소음 바닥값)
DB_MAX = 90.0   # 원시값 1023에 대응하는 최대 dB


class Processor:
    def __init__(self):
        # 이동평균 버퍼
        self._buffers = {
            "temp":     deque(maxlen=MOVING_AVG_N),
            "humidity": deque(maxlen=MOVING_AVG_N),
            "light":    deque(maxlen=MOVING_AVG_N),
            "sound":    deque(maxlen=MOVING_AVG_N),
        }

        # 수면 상태
        self._is_sleeping        = False
        self._low_light_since    = None   # 조도 임계값 이하 유지 시작 시각
        self._pir_times          = deque()  # PIR 감지 시각 목록
        self._sleep_end_time     = None   # 수면 종료 시각 (재개 판단용)

    # =============================================
    # 이동평균
    # =============================================
    def _moving_average(self, key: str, value: int | float) -> float:
        """버퍼에 값 추가 후 이동평균 반환"""
        self._buffers[key].append(value)
        return sum(self._buffers[key]) / len(self._buffers[key])

    # =============================================
    # 단위 변환
    # =============================================
    def _raw_to_lux(self, raw: int) -> float:
        """
        CDS 원시값(0~1023) → lux 근사 변환
        log 스케일 매핑 적용 (CDS 센서 특성 반영)

        ⚠️ 주의: 범용 아두이노 호환 CDS 센서 기준 경험적 근사값
        센서 모델 및 회로 구성(분압 저항값 등)에 따라 실제값과 오차 발생 가능
        정밀 측정이 필요한 경우 실측 환경에서 캘리브레이션 필요
        """
        if raw <= 0:
            return 0.0

        # 0~1023 → 0.0~1.0 정규화
        normalized = raw / 1023.0

        # log 스케일 매핑: lux = LUX_MAX * (normalized ^ 2)
        # 저조도 구간에서 민감하게, 고조도 구간에서 완만하게 반응하는 CDS 특성 반영
        lux = LUX_MAX * (normalized ** 2)

        return round(lux, 1)

    def _raw_to_db(self, raw: int) -> float:
        """
        사운드 센서 원시값(0~1023) → dB 근사 변환
        log 스케일 매핑 적용 (음압 특성 반영)

        ⚠️ 주의: 범용 아두이노 호환 사운드 센서(KY-038 등) 기준 경험적 근사값
        센서 모델 및 마이크 감도에 따라 실제값과 오차 발생 가능
        정밀 측정이 필요한 경우 실측 환경에서 캘리브레이션 필요
        """
        if raw <= 0:
            return DB_MIN

        # 0~1023 → DB_MIN~DB_MAX 범위로 log 스케일 매핑
        # dB는 음압의 log 스케일이므로 log10 기반 매핑 적용
        db = DB_MIN + (DB_MAX - DB_MIN) * (math.log10(raw + 1) / math.log10(1024))

        return round(db, 1)

    # =============================================
    # 타임존 추가
    # =============================================
    def _add_timezone(self, time_str: str) -> str:
        """
        아두이노 RTC 시각에 한국 타임존 추가
        "2026-05-11T23:30:00" → "2026-05-11T23:30:00+09:00"
        """
        if time_str.endswith("+09:00"):
            return time_str
        return time_str + "+09:00"

    # =============================================
    # 수면 이벤트 감지
    # =============================================
    def _detect_sleep_event(self, light_raw: int, motion: int) -> str | None:
        """
        수면 이벤트 감지
        조도 임계값 비교는 변환 전 원시값(0~1023) 기준으로 수행
        반환값: "sleep_start" | "sleep_end" | "sleep_resume" | None
        """
        now = time.time()

        # ---- 수면 중이 아닌 경우: 수면 시작 감지 ----
        if not self._is_sleeping:

            # 수면 재개 감지 (종료 후 5분 내 조도 임계값 이하)
            if (self._sleep_end_time is not None
                    and now - self._sleep_end_time <= RESUME_WINDOW
                    and light_raw <= SLEEP_LIGHT_THRESHOLD):
                self._is_sleeping = True
                self._sleep_end_time = None
                self._low_light_since = None
                logger.info("수면 재개 감지")
                return "sleep_resume"

            # 수면 시작 감지 (조도 임계값 이하 60초 유지)
            if light_raw <= SLEEP_LIGHT_THRESHOLD:
                if self._low_light_since is None:
                    self._low_light_since = now  # 타이머 시작
                elif now - self._low_light_since >= SLEEP_START_SECONDS:
                    self._is_sleeping = True
                    self._low_light_since = None
                    logger.info("수면 시작 감지")
                    return "sleep_start"
            else:
                self._low_light_since = None  # 조도 올라가면 타이머 리셋

        # ---- 수면 중인 경우: 수면 종료 감지 ----
        else:
            if motion:
                self._pir_times.append(now)

            # 10초 지난 PIR 감지 기록 제거
            while self._pir_times and now - self._pir_times[0] > WAKE_PIR_WINDOW:
                self._pir_times.popleft()

            # 10초 내 PIR 3회 이상 감지
            if len(self._pir_times) >= WAKE_PIR_COUNT:
                self._is_sleeping = False
                self._sleep_end_time = now
                self._pir_times.clear()
                self._low_light_since = None
                logger.info("수면 종료 감지")
                return "sleep_end"

        return None

    # =============================================
    # 전처리 메인
    # =============================================
    def process(self, raw: dict) -> dict:
        """
        수신된 raw 데이터 전처리
        반환 형태: {
            "temperature": float,   # 이동평균 적용 (°C)
            "humidity":    float,   # 이동평균 적용 (%)
            "light":       float,   # 이동평균 → lux 근사 변환
            "sound":       float,   # 이동평균 → dB 근사 변환
            "motion":      bool,
            "arduino_time": str,    # 타임존 추가된 시각
            "event":       str | None  # 수면 이벤트 (없으면 None)
        }
        """
        # 이동평균 적용
        temperature = round(self._moving_average("temp",     raw["temp"]),     1)
        humidity    = round(self._moving_average("humidity", raw["humidity"]), 1)
        light_raw   = round(self._moving_average("light",    raw["light"]))
        sound_raw   = round(self._moving_average("sound",    raw["sound"]))
        motion      = bool(raw["motion"])
        arduino_time = self._add_timezone(raw["time"])

        # 단위 변환 (이동평균 적용 후 변환)
        light_lux = self._raw_to_lux(light_raw)   # 원시값 → lux
        sound_db  = self._raw_to_db(sound_raw)    # 원시값 → dB

        # 수면 이벤트 감지 (조도 임계값 비교는 원시값 기준 유지)
        event = self._detect_sleep_event(light_raw, motion)

        return {
            "temperature":  temperature,
            "humidity":     humidity,
            "light":        light_lux,    # lux 단위로 FastAPI 전송
            "sound":        sound_db,     # dB 단위로 FastAPI 전송
            "motion":       motion,
            "arduino_time": arduino_time,
            "event":        event,
        }