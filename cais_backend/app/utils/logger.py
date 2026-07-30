"""
Logger - Logging Utilities

This module provides logging utilities for the application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str = "cais",
    log_file: Optional[str] = None,
    level: str = "INFO",
    max_bytes: int = 10_485_760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up a logger with console and file handlers.

    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "cais") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
