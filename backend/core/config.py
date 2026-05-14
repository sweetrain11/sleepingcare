from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TimescaleDB
    database_url: str = "postgresql://postgres:password@localhost:5432/sleepingcare_db"

    # Anthropic Claude API
    anthropic_api_key: str = ""

    # MQTT 브로커
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # FastAPI 서버
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# 전역 설정 인스턴스
settings = Settings()
