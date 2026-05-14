"""
routers/sensors.py
/api/sensors  - 센서 데이터 수신, 수동 테스트
/ws/realtime  - WebSocket 실시간 센서 스트림
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from asyncpg import Connection

from core.database import get_conn
from models.schemas import SensorDataIn, SensorDataOut, MockSensorIn

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket 연결 관리
_ws_clients: set[WebSocket] = set()


async def broadcast_sensor(data: dict):
    """연결된 모든 WebSocket 클라이언트에 센서 데이터 브로드캐스트"""
    if not _ws_clients:
        return
    message = json.dumps(data, default=str)
    disconnected = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _ws_clients.difference_update(disconnected)


# --------------------------------------------------
# REST API
# --------------------------------------------------

@router.post("/data", response_model=SensorDataOut)
async def receive_sensor_data(
    body: SensorDataIn,
    conn: Connection = Depends(get_conn),
):
    """
    POST /api/sensors/data
    라즈베리파이에서 전처리된 센서 데이터 수신 → DB 저장 → WebSocket 브로드캐스트
    """
    now = datetime.now(timezone.utc)

    await conn.execute(
        """
        INSERT INTO sensor_data
            (time, arduino_time, temperature, humidity, light, sound, motion)
        VALUES
            ($1, $2, $3, $4, $5, $6, $7)
        """,
        now,
        body.arduino_time,
        body.temperature,
        body.humidity,
        body.light,
        body.sound,
        body.motion,
    )

    # WebSocket 브로드캐스트
    await broadcast_sensor({
        "time": now.isoformat(),
        "arduino_time": body.arduino_time.isoformat() if body.arduino_time else None,
        "temperature": body.temperature,
        "humidity": body.humidity,
        "light": body.light,
        "sound": body.sound,
        "motion": body.motion,
    })

    return SensorDataOut(success=True, time=now)


@router.post("/mock", response_model=SensorDataOut)
async def create_mock_data(
    body: MockSensorIn,
    conn: Connection = Depends(get_conn),
):
    """
    POST /api/sensors/mock
    하드웨어 없이 수동으로 테스트 데이터 생성
    프론트엔드 개발 및 점수 테스트용
    """
    now = datetime.now(timezone.utc)

    await conn.execute(
        """
        INSERT INTO sensor_data
            (time, arduino_time, temperature, humidity, light, sound, motion)
        VALUES
            ($1, $1, $2, $3, $4, $5, $6)
        """,
        now,
        body.temperature,
        body.humidity,
        body.light,
        body.sound,
        body.motion,
    )

    await broadcast_sensor({
        "time": now.isoformat(),
        "arduino_time": now.isoformat(),
        "temperature": body.temperature,
        "humidity": body.humidity,
        "light": body.light,
        "sound": body.sound,
        "motion": body.motion,
    })

    return SensorDataOut(success=True, time=now)


# --------------------------------------------------
# WebSocket
# --------------------------------------------------

@router.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """
    WS /ws/realtime
    실시간 센서 데이터 스트림
    클라이언트 연결 유지 + ping/pong
    """
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"WebSocket 연결: 현재 {len(_ws_clients)}명")

    try:
        while True:
            # 클라이언트 메시지 대기 (ping 유지용)
            await asyncio.wait_for(websocket.receive_text(), timeout=30)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _ws_clients.discard(websocket)
        logger.info(f"WebSocket 해제: 현재 {len(_ws_clients)}명")
