from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==============================================
# 센서 데이터
# ==============================================

class SensorDataIn(BaseModel):
    """라즈베리파이 → FastAPI 센서 데이터 수신"""
    arduino_time: Optional[datetime] = None
    temperature: Optional[float] = Field(None, ge=-40, le=80)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    light: Optional[int] = Field(None, ge=0, le=1023)
    sound: Optional[int] = Field(None, ge=0, le=1023)
    motion: bool = False


class SensorDataOut(BaseModel):
    """센서 데이터 저장 응답"""
    success: bool
    time: datetime


class MockSensorIn(BaseModel):
    """수동 테스트 데이터 생성용"""
    temperature: float = Field(20.0, ge=-40, le=80)
    humidity: float = Field(50.0, ge=0, le=100)
    light: int = Field(50, ge=0, le=1023)
    sound: int = Field(200, ge=0, le=1023)
    motion: bool = False


# ==============================================
# 수면 이벤트
# ==============================================

class SleepEventIn(BaseModel):
    """라즈베리파이 수면 이벤트 수신"""
    event: str          # sleep_start | sleep_end | sleep_resume
    timestamp: Optional[datetime] = None


# ==============================================
# 수면 세션 / 점수
# ==============================================

class SleepScoreOut(BaseModel):
    """수면 점수 조회 응답"""
    session_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_min: Optional[int]
    avg_temperature: Optional[float]
    avg_humidity: Optional[float]
    avg_light: Optional[float]
    avg_sound: Optional[float]
    motion_count: int
    regularity_diff_min: Optional[int]
    env_score: Optional[int]
    pattern_score: Optional[int]
    total_score: Optional[int]
    coaching: Optional["CoachingOut"] = None


class SleepHistoryOut(BaseModel):
    """수면 이력 조회 응답"""
    range: str
    sessions: list[SleepScoreOut]


# ==============================================
# AI 코칭
# ==============================================

class CoachingGenerateIn(BaseModel):
    """코칭 생성 요청"""
    session_id: int


class CoachingOut(BaseModel):
    """코칭 결과 응답"""
    id: int
    session_id: int
    good_points: Optional[str]
    bad_points: Optional[str]
    weekly_goal: Optional[str]
    created_at: datetime


# ==============================================
# 헬스체크
# ==============================================

class HealthOut(BaseModel):
    status: str
    db: str
    mqtt: str
