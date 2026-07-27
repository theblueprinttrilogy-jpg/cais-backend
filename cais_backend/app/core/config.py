"""
Application configuration and settings management for CAIS backend.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GCP_PROJECT: str = "cais-uploader-production-2026"
    GCP_CREDENTIALS_JSON: str = "app/credentials/service-account.json"
    GCS_BUCKET_PLANS: str = "cais-plans-storage-2026"
    ROOT_FOLDER_ID: str = "1BIDavBaxBScLnjJfFTvnfLaOEPw0msPp"
    POSTGRES_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cais_db"
    RABBITMQ_URI: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "plan_processing"
    RABBITMQ_ROUTING_KEY: str = "plan.uploaded"
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REFRESH_TOKEN: Optional[str] = None
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"


settings = Settings()
