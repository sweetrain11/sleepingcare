# =============================================
# receiver.py
# 블루투스 수신 + JSON 파싱
# HC-06 → 라즈베리파이 시리얼 포트
# =============================================

import serial
import json
import logging

logger = logging.getLogger(__name__)

class BluetoothReceiver:
    def __init__(self, port: str = "/dev/rfcomm0", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def connect(self):
        """블루투스 시리얼 포트 연결"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=5)
            logger.info(f"블루투스 연결 성공: {self.port}")
        except serial.SerialException as e:
            logger.error(f"블루투스 연결 실패: {e}")
            raise

    def disconnect(self):
        """블루투스 시리얼 포트 연결 해제"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("블루투스 연결 해제")

    def read(self) -> dict | None:
        """
        시리얼 포트에서 한 줄 읽기 + JSON 파싱
        파싱 실패 시 None 반환 (해당 데이터 버림)
        반환 형태: {
            "temp": int,
            "humidity": int,
            "light": int,
            "sound": int,
            "motion": int,  # 0 or 1
            "time": str     # "YYYY-MM-DDTHH:MM:SS"
        }
        """
        if not self.serial or not self.serial.is_open:
            logger.warning("시리얼 포트가 열려있지 않음")
            return None

        try:
            line = self.serial.readline().decode("utf-8").strip()
            if not line:
                return None

            data = json.loads(line)

            # 필수 키 확인
            required_keys = {"temp", "humidity", "light", "sound", "motion", "time"}
            if not required_keys.issubset(data.keys()):
                logger.warning(f"필수 키 누락: {line}")
                return None

            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"JSON 파싱 실패: {e} | 원본: {line}")
            return None
        except serial.SerialException as e:
            logger.error(f"시리얼 읽기 오류: {e}")
            raise
