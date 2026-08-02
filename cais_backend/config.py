"""
CAIS Code Compliance - Application Configuration

This module defines the configuration settings for the application,
loading values from environment variables with sensible defaults.
All settings are validated using Pydantic.

Version: 10.0
"""

from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings.

    All fields can be overridden by environment variables.
    For example, APP_NAME can be set via the APP_NAME env var.
    """

    # Application metadata
    APP_NAME: str = "CAIS Code Compliance"
    APP_VERSION: str = "10.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/cais"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Google Cloud Platform
    GCP_PROJECT_ID: Optional[str] = None
    GCP_STORAGE_BUCKET: Optional[str] = None
    GCP_CREDENTIALS_PATH: Optional[str] = None

    # AI / Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Hugging Face
    HF_HOME: str = "/app/model_cache"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"

    # RabbitMQ (optional)
    RABBITMQ_URL: Optional[str] = None

    # Other
    MAX_UPLOAD_SIZE: int = 104857600  # 100 MB in bytes
    TEMP_DIR: str = "/tmp"

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list_field(cls, value):
        """
        Parse environment variables that may be strings (comma-separated or "*")
        into proper List[str] values.

        If the value is already a list, return it unchanged.
        If the value is a string, split by commas and strip whitespace.
        If the string is "*", keep it as ["*"] (wildcard).
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # If it's a single asterisk, keep it as a list containing "*"
            if value == "*":
                return ["*"]
            # Otherwise split by commas, strip, and filter out empty strings
            return [item.strip() for item in value.split(",") if item.strip()]
        # If it's None or other type, return empty list as fallback
        return []

    class Config:
        """Pydantic BaseSettings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create a global settings object to be imported elsewhere
settings = Settings()
