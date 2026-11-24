from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lead and Product Management API"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/ashutosh"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "lead-management.events"
    outbox_poll_seconds: float = 2
    cache_ttl_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

