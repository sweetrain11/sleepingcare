# =============================================
# main.py
# SleepingCare 라즈베리파이 메인 실행 파일
# receiver → processor → publisher 흐름 제어
# =============================================

import time
import logging
from receiver  import BluetoothReceiver
from processor import Processor
from publisher import MQTTPublisher

# =============================================
# 설정
# =============================================
BT_PORT      = "/dev/rfcomm0"   # 블루투스 시리얼 포트
MQTT_HOST    = "192.168.x.x"    # 노트북 IP (핫스팟 or 공유 와이파이 기준)
MQTT_PORT    = 1883

RETRY_DELAY  = 5                # 재연결 대기 시간 (초)

# =============================================
# 로깅 설정
# =============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    receiver  = BluetoothReceiver(port=BT_PORT)
    processor = Processor()
    publisher = MQTTPublisher(broker_host=MQTT_HOST, broker_port=MQTT_PORT)

    # MQTT 연결
    publisher.connect()

    # 블루투스 연결 (실패 시 재시도)
    while True:
        try:
            receiver.connect()
            break
        except Exception as e:
            logger.error(f"블루투스 연결 실패, {RETRY_DELAY}초 후 재시도: {e}")
            time.sleep(RETRY_DELAY)

    logger.info("SleepingCare 라즈베리파이 시작")

    # 메인 루프
    while True:
        try:
            # 1. 블루투스 수신 + JSON 파싱
            raw = receiver.read()
            if raw is None:
                continue

            # 2. 전처리 (이동평균, 타임존, 이벤트 감지)
            processed = processor.process(raw)

            # 3. 센서 데이터 MQTT publish
            publisher.publish_sensors(processed)

            # 4. 수면 이벤트 publish (이벤트가 있을 때만)
            if processed["event"]:
                publisher.publish_event(
                    event        = processed["event"],
                    arduino_time = processed["arduino_time"],
                )

        except Exception as e:
            logger.error(f"처리 중 오류 발생: {e}")

            # 블루투스 연결 끊김 시 재연결
            logger.info(f"{RETRY_DELAY}초 후 블루투스 재연결 시도")
            time.sleep(RETRY_DELAY)
            try:
                receiver.disconnect()
                receiver.connect()
            except Exception as reconnect_err:
                logger.error(f"재연결 실패: {reconnect_err}")


if __name__ == "__main__":
    run()
