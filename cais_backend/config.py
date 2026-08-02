"""
CAIS Code Compliance - Application Configuration

This module defines the configuration settings for the application,
loading values from environment variables with sensible defaults.
All settings are validated using Pydantic.

Version: 10.0
"""

from typing import Any, Optional, List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.

    All fields can be overridden by environment variables.
    For example, APP_NAME can be set via the APP_NAME env var.
    """

    # ===== Application =====
    APP_NAME: str = "CAIS Code Compliance"
    APP_VERSION: str = "10.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ===== Database =====
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/cais"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ===== Redis & RabbitMQ =====
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_DB: int = 0
    RABBITMQ_URL: Optional[str] = None

    # ===== Ollama & AI =====
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    HF_HOME: str = "/app/model_cache"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"

    # ===== Security & JWT =====
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # ===== CORS / Hosts =====
    # Use Any to prevent pydantic-settings from attempting json.loads() on these
    # fields before the validator runs. The validator will parse strings properly.
    ALLOWED_ORIGINS: Any = ["*"]
    ALLOWED_HOSTS: Any = ["*"]

    # ===== Storage & OCR =====
    STORAGE_PATH: str = "/app/storage"
    MAX_UPLOAD_SIZE: int = 52428800  # 50 MB in bytes
    OCR_DPI: int = 200
    OCR_LANGUAGE: str = "eng+spa"  # English and Spanish

    # ===== Stripe & Email =====
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    TRIAL_DAYS: int = 30
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ===== Google Cloud & Legacy Fields =====
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GCP_PROJECT_ID: Optional[str] = None
    GCP_PROJECT: Optional[str] = None
    GCP_CREDENTIALS_JSON: Optional[str] = None
    GCS_BUCKET_PLANS: Optional[str] = None
    ROOT_FOLDER_ID: Optional[str] = None
    POSTGRES_DSN: Optional[str] = None
    RABBITMQ_URI: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REFRESH_TOKEN: Optional[str] = None

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list_field(cls, value: Any) -> List[str]:
        """
        Parse environment variables that may be strings (comma-separated or "*")
        into proper List[str] values.

        If the value is already a list, return it unchanged.
        If the value is a string, split by commas and strip whitespace.
        If the string is "*", keep it as ["*"] (wildcard).
        If the value is None or any other type, return an empty list.
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # If it's a single asterisk, keep it as a list containing "*"
            if value == "*":
                return ["*"]
            # Otherwise split by commas, strip, and filter out empty strings
            return [item.strip() for item in value.split(",") if item.strip()]
        # Fallback: return empty list
        return []

    class Config:
        """Pydantic BaseSettings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment variables


# Create a global settings object to be imported elsewhere
settings = Settings()
