# SleepingCare

수면 환경·패턴 데이터를 자동으로 진단하고 AI가 개선 방향을 제시하는 플랫폼.

Arduino → Raspberry Pi → MQTT → FastAPI → React 흐름으로 동작하며, Claude AI가 수면 코칭 텍스트를 생성한다.

---

## 시스템 아키텍처

```
Arduino (센서 측정)
    ↓ HC-06 블루투스
Raspberry Pi (수신 · 가공 · 발행)
    ↓ MQTT
FastAPI 백엔드 (저장 · 점수 계산 · AI 코칭)
    ↓ REST / WebSocket
React 프론트엔드 (대시보드 · 리포트 · 코칭)
```

---

## 수면 점수 기준

### 환경 점수 (40점 만점 · 항목별 10점)

| 항목 | 단위 | 만점 구간 | 감점 구간 |
|---|---|---|---|
| 온도 | °C | 15–19°C → 10점 | 13–21°C → 6점, 21–23°C → 3점, 그 외 → 0점 |
| 습도 | % RH | 40–60% → 10점 | 35–65% → 6점, 30–70% → 3점, 그 외 → 0점 |
| 조도 | lux | 0–5 lux → 10점 | 10 lux 이하 → 8점, 30 lux 이하 → 5점, 100 lux 이하 → 2점, 초과 → 0점 |
| 소음 | dB | 30 dB 미만 → 10점 | 40 dB 이하 → 7점, 55 dB 이하 → 4점, 65 dB 이하 → 1점, 초과 → 0점 |

> 센서 누락 시 각 항목 5점 기본 반영

### 패턴 점수 (60점 만점 · 항목별 20점)

| 항목 | 만점 구간 | 감점 기준 |
|---|---|---|
| 수면 시간 | 7–9시간 (420–540분) → 20점 | 1시간 구간마다 5점 감점, 4시간 미만 → 0점 |
| 규칙성 | 전날 취침 시각 편차 0–29분 → 20점 | 30분마다 5점 감점, 120분 이상 → 0점 |
| 뒤척임 | 0–4회 → 20점 | 5회마다 5점 감점, 20회 이상 → 0점 |

> 첫 세션(비교 대상 없음) 시 규칙성 10점 기본 반영

---

## 프로젝트 구조

```
sleeping-care/
├── arduino/
│   └── sleeping_care.ino              # 통합 센서 스케치 (DHT11, CDS, PIR, 사운드, RTC, HC-06)
│
├── raspberry/
│   ├── main.py                        # 메인 실행 파일 (receiver → processor → publisher 흐름 제어)
│   ├── receiver.py                    # HC-06 블루투스 수신 + JSON 파싱
│   ├── processor.py                   # 이동평균(N=5), 단위 변환(ADC→lux/dB), 수면 이벤트 감지
│   └── publisher.py                   # MQTT 토픽별 publish (센서 6개 + 이벤트 3개)
│
├── backend/
│   ├── .env                           # 환경변수 (DB URL, Anthropic API 키, MQTT 설정)
│   ├── .env.example                   # 환경변수 템플릿
│   ├── requirements.txt               # Python 패키지 목록
│   ├── schema.sql                     # TimescaleDB 테이블 정의
│   ├── update_db_ip.ps1               # DB 접속 IP 일괄 변경 스크립트 (Windows)
│   ├── main.py                        # FastAPI 진입점 (라우터 등록, CORS, MQTT 시작)
│   ├── core/
│   │   ├── config.py                  # .env 로드 (pydantic-settings)
│   │   └── database.py                # TimescaleDB 연결 (asyncpg)
│   ├── routers/
│   │   ├── sensors.py                 # /api/sensors (데이터 수신, 수동 테스트, WebSocket)
│   │   ├── sleep.py                   # /api/sleep (상태 조회, 수동 제어, 이력 조회)
│   │   └── coaching.py                # /api/coaching (AI 코칭 생성 · 조회)
│   ├── models/
│   │   └── schemas.py                 # Pydantic 요청/응답 스키마
│   ├── services/
│   │   ├── sleep_score.py             # 수면 점수 계산 순수 함수 (환경 40점 + 패턴 60점)
│   │   ├── sleep_session.py           # 수면 세션 종료 처리 (센서 집계 · 규칙성 · 점수 · DB 저장)
│   │   └── claude_coaching.py         # Claude API 연동 (코칭 텍스트 생성)
│   └── mqtt/
│       └── subscriber.py              # MQTT subscribe → 센서 저장, 수면 이벤트 라우팅
│
└── frontend/
    ├── index.html                     # Vite 진입점 HTML
    ├── vite.config.js                 # Vite 설정 (포트 5174, 프록시 등)
    ├── tailwind.config.js             # TailwindCSS 설정
    ├── postcss.config.js              # PostCSS 설정
    ├── public/
    │   ├── manifest.json              # PWA 설정 (앱 이름, 아이콘, 색상)
    │   ├── favicon.svg                # 파비콘
    │   └── sw.js                      # Service Worker (PWA 오프라인 지원)
    └── src/
        ├── main.jsx                   # React 진입점
        ├── index.css                  # 전역 스타일 (Tailwind 베이스)
        ├── App.jsx                    # 라우팅 설정 (Dashboard / Report / Coaching / Help)
        ├── pages/
        │   ├── Dashboard.jsx          # 실시간 센서 카드 + 수면 시작/종료 제어
        │   ├── Report.jsx             # 1일 상세 · 주간/월간 점수 차트 · 수면 패턴 캘린더
        │   ├── Coaching.jsx           # AI 코칭 카드 (1일 · 7일 · 30일 범위)
        │   └── Help.jsx               # 도움말 (아키텍처, 라이브러리, 로직, 버전)
        ├── components/
        │   ├── Layout.jsx             # 네비게이션 + 공통 래퍼
        │   ├── SensorCard.jsx         # 실시간 센서 카드
        │   ├── ScoreGauge.jsx         # 수면 점수 게이지 (Recharts)
        │   ├── WeeklyChart.jsx        # 주간/월간 점수 차트 (Recharts LineChart)
        │   └── CoachingCard.jsx       # AI 코칭 카드 UI
        └── hooks/
            └── useWebSocket.js        # WebSocket 커스텀 훅 (실시간 센서 · 수면 상태 수신)
```

---

## 주요 MQTT 토픽

| 토픽 | 방향 | 설명 |
|---|---|---|
| `sleepingcare/sensors/temperature` | Raspberry → Backend | 온도 (°C, 이동평균 적용) |
| `sleepingcare/sensors/humidity` | Raspberry → Backend | 습도 (%, 이동평균 적용) |
| `sleepingcare/sensors/light` | Raspberry → Backend | 조도 (lux, ADC → lux 변환) |
| `sleepingcare/sensors/sound` | Raspberry → Backend | 소음 (dB, ADC → dB 변환) |
| `sleepingcare/sensors/motion` | Raspberry → Backend | 움직임 감지 (bool) |
| `sleepingcare/sensors/time` | Raspberry → Backend | Arduino 타임스탬프 (버퍼 flush 트리거) |
| `sleepingcare/events/sleep_start` | Raspberry → Backend | 수면 시작 이벤트 |
| `sleepingcare/events/sleep_end` | Raspberry → Backend | 수면 종료 이벤트 |
| `sleepingcare/events/sleep_resume` | Raspberry → Backend | 수면 재개 이벤트 |

---

## 주요 API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 서버·DB·MQTT 상태 확인 |
| POST | `/api/sensors/data` | 센서 데이터 수신 |
| POST | `/api/sensors/mock` | 테스트용 센서 데이터 수동 입력 |
| WS  | `/ws/realtime` | 실시간 센서 데이터 스트림 |
| GET | `/api/sleep/status` | 현재 수면 상태 조회 |
| POST | `/api/sleep/start` | 수면 시작 (수동) |
| POST | `/api/sleep/end` | 수면 종료 (수동) |
| GET | `/api/sleep/score/{session_id}` | 수면 세션 점수 조회 |
| GET | `/api/sleep/history?range=day\|week\|month` | 수면 이력 조회 |
| POST | `/api/coaching/generate` | 단일 세션 AI 코칭 생성 |
| POST | `/api/coaching/range/generate` | 범위 기반 AI 코칭 생성 |
| GET | `/api/coaching/range?range=day\|week\|month` | 저장된 범위 코칭 조회 |

---

## 환경 설정

`backend/.env.example`을 복사해 `.env`를 생성하고 값을 채운다.

```env
DATABASE_URL=postgresql://user:password@host:5432/sleepingcare_db
ANTHROPIC_API_KEY=sk-ant-...
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
APP_HOST=0.0.0.0
APP_PORT=8001
```

---

## 실행

### 백엔드
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

### Raspberry Pi
```bash
cd raspberry
python main.py
```

---

## 버전

v0.0.1
