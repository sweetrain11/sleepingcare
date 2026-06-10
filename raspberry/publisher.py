# =============================================
# publisher.py
# MQTT 토픽별 publish
# =============================================

import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# ---- MQTT 토픽 ----
SENSOR_TOPICS = {
    "temperature":  "sleepingcare/sensors/temperature",
    "humidity":     "sleepingcare/sensors/humidity",
    "light":        "sleepingcare/sensors/light",
    "sound":        "sleepingcare/sensors/sound",
    "motion":       "sleepingcare/sensors/motion",
    "arduino_time": "sleepingcare/sensors/time",
}

EVENT_TOPICS = {
    "sleep_start":  "sleepingcare/events/sleep_start",
    "sleep_end":    "sleepingcare/events/sleep_end",
    "sleep_resume": "sleepingcare/events/sleep_resume",
}


class MQTTPublisher:
    def __init__(self, broker_host: str, broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(f"MQTT 브로커 연결 성공: {self.broker_host}:{self.broker_port}")
        else:
            logger.error(f"MQTT 브로커 연결 실패: reason_code={reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        logger.warning(f"MQTT 브로커 연결 끊김: reason_code={reason_code}")

    def connect(self):
        """MQTT 브로커 연결"""
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()

    def disconnect(self):
        """MQTT 브로커 연결 해제"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT 연결 해제")

    def publish_sensors(self, data: dict):
        """
        센서 데이터 토픽별 publish
        time 값 기준으로 FastAPI에서 세트 묶음 처리
        """
        for key, topic in SENSOR_TOPICS.items():
            value = data.get(key)
            if value is None:
                continue

            # bool은 json.dumps로 true/false 직렬화, 나머지는 str 변환
            payload = json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value)
            self.client.publish(topic, payload, qos=1)
            logger.debug(f"publish: {topic} = {payload}")

    def publish_event(self, event: str, arduino_time: str):
        """
        수면 이벤트 publish
        payload: 이벤트 발생 시각 (arduino_time)
        """
        topic = EVENT_TOPICS.get(event)
        if not topic:
            logger.warning(f"알 수 없는 이벤트: {event}")
            return

        self.client.publish(topic, arduino_time, qos=1)
        logger.info(f"이벤트 publish: {topic} = {arduino_time}")
