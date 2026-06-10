"""
main.py
FastAPI 진입점
- CORS 설정 (프론트 5174 허용)
- 라우터 등록
- 앱 시작/종료 시 DB 풀 및 MQTT 초기화
"""
import asyncio
import sys

# Windows에서 asyncpg 호환을 위해 SelectorEventLoop 강제 사용
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import get_pool, close_pool
from routers import sensors, sleep, coaching
from mqtt.subscriber import start_mqtt, stop_mqtt, is_mqtt_connected
from models.schemas import HealthOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# 앱 생명주기
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    logger.info("SleepingCare 서버 시작")
    await get_pool()           # DB 커넥션 풀 초기화
    loop = asyncio.get_event_loop()
    start_mqtt(loop)           # MQTT 브로커 연결
    yield
    # 종료
    stop_mqtt()
    await close_pool()
    logger.info("SleepingCare 서버 종료")


# --------------------------------------------------
# FastAPI 앱 생성
# --------------------------------------------------

app = FastAPI(
    title="SleepingCare API",
    description="수면 환경·패턴 데이터를 자동으로 진단하고 AI가 개선 방향을 제시하는 플랫폼",
    version="0.0.1",
    lifespan=lifespan,
)

# CORS 설정 (React 개발 서버 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용: 로컬 네트워크 폰 접속 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# 라우터 등록
# --------------------------------------------------

app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
app.include_router(sleep.router,   prefix="/api/sleep",   tags=["sleep"])
app.include_router(coaching.router, prefix="/api/coaching", tags=["coaching"])

# WebSocket은 prefix 없이 /ws/realtime 경로로 직접 등록
app.add_api_websocket_route("/ws/realtime", sensors.websocket_realtime)


# --------------------------------------------------
# 헬스체크
# --------------------------------------------------

@app.get("/health", response_model=HealthOut, tags=["health"])
async def health_check():
    """GET /health — 서버 및 DB, MQTT 상태 확인"""
    # DB 연결 확인
    db_status = "ok"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        db_status = f"error: {e}"

    mqtt_status = "connected" if is_mqtt_connected() else "disconnected"

    return HealthOut(
        status="ok",
        db=db_status,
        mqtt=mqtt_status,
    )
