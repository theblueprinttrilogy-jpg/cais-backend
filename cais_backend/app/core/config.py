"""
Configuration module for the CAIS backend.

All settings are loaded from environment variables using pydantic-settings.
No hardcoded fallbacks or local file dependencies are allowed.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # GCP configuration
    GCP_PROJECT: str
    GCP_CREDENTIALS_JSON: Optional[str] = None  # Path to service account JSON file

    # PostgreSQL (asyncpg)
    POSTGRES_DSN: str  # e.g., postgresql+asyncpg://user:pass@host:5432/db

    # RabbitMQ (aio-pika)
    RABBITMQ_URI: str  # e.g., amqp://user:pass@host:5672/

    # Redis (for WebSocket state / pub/sub)
    REDIS_URL: str  # e.g., redis://host:6379/0

    # GCS bucket name for uploaded plans
    GCS_BUCKET_PLANS: str

    # RabbitMQ exchange and routing keys
    RABBITMQ_EXCHANGE: str = "plan_processing"
    RABBITMQ_ROUTING_KEY: str = "plan.uploaded"


# Singleton instance
settings = Settings()
