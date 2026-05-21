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

### 환경 점수 (40점)
| 항목 | 만점 기준 | 감점 기준 |
|---|---|---|
| 온도 | 18 ~ 22°C | 1°C 벗어날 때마다 2점 |
| 습도 | 40 ~ 60% | 5% 벗어날 때마다 2점 |
| 조도 | 100 이하 (ADC) | 초과 시 선형 감점 |
| 소음 | 300 이하 (ADC) | 초과 시 선형 감점 |

### 패턴 점수 (60점)
| 항목 | 만점 기준 | 감점 기준 |
|---|---|---|
| 수면 시간 | 7 ~ 9시간 | 1시간 벗어날 때마다 5점 |
| 규칙성 | 전날과 취침 시각 동일 | 30분마다 5점 |
| 뒤척임 | 0회 | 5회마다 5점 |

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
│   ├── processor.py                   # 이동평균(N=5), 타임존 추가, 수면 이벤트 감지
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
│   │   ├── sleep.py                   # /api/sleep (점수 조회, 이력 조회)
│   │   └── coaching.py                # /api/coaching (AI 코칭 생성)
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
        │   ├── Dashboard.jsx          # 실시간 센서 카드 + 오늘 수면 점수
        │   ├── Report.jsx             # 주간/월간 점수 차트 + 수면 패턴 캘린더
        │   ├── Coaching.jsx           # AI 코칭 카드 목록
        │   └── Help.jsx               # 도움말 (아키텍처, 라이브러리, 로직, 버전 v0.0.1)
        ├── components/
        │   ├── Layout.jsx             # 네비게이션 + 공통 래퍼
        │   ├── SensorCard.jsx         # 실시간 센서 카드 (WebSocket 연결)
        │   ├── ScoreGauge.jsx         # 수면 점수 게이지 (Recharts)
        │   ├── WeeklyChart.jsx        # 주간/월간 점수 차트 (Recharts LineChart)
        │   └── CoachingCard.jsx       # AI 코칭 카드 UI
        └── hooks/
            └── useWebSocket.js        # WebSocket 커스텀 훅 (실시간 센서 데이터 수신)
```

---

## 주요 MQTT 토픽

| 토픽 | 방향 | 설명 |
|---|---|---|
| `sleepingcare/sensors/temperature` | Raspberry → Backend | 온도 (°C) |
| `sleepingcare/sensors/humidity` | Raspberry → Backend | 습도 (%) |
| `sleepingcare/sensors/light` | Raspberry → Backend | 조도 (ADC 0~1023) |
| `sleepingcare/sensors/sound` | Raspberry → Backend | 소음 (ADC 0~1023) |
| `sleepingcare/sensors/motion` | Raspberry → Backend | 움직임 (bool) |
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
| GET | `/api/sleep/score/{session_id}` | 수면 세션 점수 조회 |
| GET | `/api/sleep/history?range=week\|month` | 수면 이력 조회 |
| POST | `/api/coaching/generate` | AI 코칭 생성 |
| WS | `/ws/realtime` | 실시간 센서 데이터 스트림 |

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
