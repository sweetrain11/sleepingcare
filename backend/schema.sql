-- ==============================================
-- SleepingCare Database Schema
-- TimescaleDB 기반 수면 데이터 스키마
-- ==============================================

-- 기존 테이블 제거 (재실행 시 초기화용)
DROP TABLE IF EXISTS coaching_results;
DROP TABLE IF EXISTS sleep_sessions;
DROP TABLE IF EXISTS sensor_data;

-- ==============================================
-- 1. sensor_data (하이퍼테이블)
-- 라즈베리파이에서 전처리된 센서 데이터 저장
-- 이동평균 N=5 적용된 값
-- ==============================================
CREATE TABLE sensor_data (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),  -- 서버 수신 시각
    arduino_time    TIMESTAMPTZ,                             -- RTC 기준 측정 시각
    temperature     FLOAT,                                   -- 온도 (°C)
    humidity        FLOAT,                                   -- 습도 (%)
    light           INT,                                     -- 조도 (0~1023)
    sound           INT,                                     -- 소음 (0~1023)
    motion          BOOLEAN         NOT NULL DEFAULT FALSE   -- PIR 모션 감지 여부
);

-- TimescaleDB 하이퍼테이블 변환 (time 컬럼 기준)
SELECT create_hypertable('sensor_data', 'time');

-- ==============================================
-- 2. sleep_sessions
-- 수면 세션 및 점수 저장
-- 라즈베리파이 이벤트(sleep_start/sleep_end)로 생성/종료
-- ==============================================
CREATE TABLE sleep_sessions (
    id                  SERIAL          PRIMARY KEY,
    start_time          TIMESTAMPTZ     NOT NULL,            -- 수면 시작 시각
    end_time            TIMESTAMPTZ,                         -- 수면 종료 시각
    duration_min        INT,                                 -- 수면 시간 (분)
    avg_temperature     FLOAT,                               -- 세션 평균 온도 (°C)
    avg_humidity        FLOAT,                               -- 세션 평균 습도 (%)
    avg_light           FLOAT,                               -- 세션 평균 조도 (0~1023)
    avg_sound           FLOAT,                               -- 세션 평균 소음 (0~1023)
    motion_count        INT             NOT NULL DEFAULT 0,  -- 수면 중 뒤척임 횟수
    regularity_diff_min INT,                                 -- 전날 대비 취침 시각 편차 (분)
    env_score           INT,                                 -- 환경 점수 (40점 만점)
    pattern_score       INT,                                 -- 패턴 점수 (60점 만점)
    total_score         INT,                                 -- 종합 점수 (100점 만점)
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ==============================================
-- 3. coaching_results
-- Claude API 코칭 결과 저장
-- ==============================================
CREATE TABLE coaching_results (
    id              SERIAL          PRIMARY KEY,
    session_id      INT             NOT NULL REFERENCES sleep_sessions(id) ON DELETE CASCADE,
    good_points     TEXT,                                    -- 잘된 점
    bad_points      TEXT,                                    -- 개선할 점
    weekly_goal     TEXT,                                    -- 이번 주 목표
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ==============================================
-- 4. range_coaching_results
-- 범위(day/week/month) 기반 코칭 결과 저장
-- ==============================================
CREATE TABLE IF NOT EXISTS range_coaching_results (
    id              SERIAL          PRIMARY KEY,
    range           VARCHAR(10)     NOT NULL,                  -- day | week | month
    good_points     TEXT,
    bad_points      TEXT,
    weekly_goal     TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- 범위별 최신 코칭 조회 최적화
CREATE INDEX IF NOT EXISTS idx_range_coaching_range_created
    ON range_coaching_results(range, created_at DESC);

-- ==============================================
-- 인덱스
-- ==============================================
-- 수면 세션 조회 최적화
CREATE INDEX idx_sleep_sessions_start_time ON sleep_sessions(start_time DESC);

-- 코칭 결과 세션 조회 최적화
CREATE INDEX idx_coaching_results_session_id ON coaching_results(session_id);
