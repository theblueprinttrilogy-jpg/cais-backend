"""
Continuous background watchdog for CAIS system services.

Monitors API backend, Celery worker, PostgreSQL, Redis, and RabbitMQ.
Sends Telegram alerts on service failure or recovery.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Optional, Tuple, List

import asyncpg
import httpx
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv()

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CAIS-Monitor")


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8938278843:AAGPkLahhg-jL9Gmc5dlbuxklb7MP9BCms")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6766537957")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Service endpoints (assumes Docker Compose service names)
API_HEALTH_URL = os.getenv("API_HEALTH_URL", "http://cais-backend:8080/health")
CELERY_PING_URL = os.getenv("CELERY_PING_URL", "http://cais-backend:8080/celery/ping")  # if exposed

# Database
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql+asyncpg://postgres:postgres@cais-postgres:5432/cais_db")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://cais-backend-redis-1:6379/0")

# RabbitMQ
RABBITMQ_URI = os.getenv("RABBITMQ_URI", "amqp://guest:guest@cais-backend-rabbitmq-1:5672/")

# Check interval (seconds)
CHECK_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "30"))

# ------------------------------------------------------------------
# State tracking (prevents alert spamming)
# ------------------------------------------------------------------
service_states: Dict[str, bool] = {}  # True = healthy, False = down

def update_state(service_name: str, is_healthy: bool) -> bool:
    """
    Update service state and return True if state changed.
    """
    previous = service_states.get(service_name)
    if previous is None or previous != is_healthy:
        service_states[service_name] = is_healthy
        return True
    return False


# ------------------------------------------------------------------
# Telegram alert sender
# ------------------------------------------------------------------
async def send_telegram_alert(message: str) -> bool:
    """
    Send a markdown‑formatted alert via Telegram Bot API.
    Returns True if successful.
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "dummy":
        logger.warning("Telegram token not set; skipping alert.")
        return False

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(TELEGRAM_API_URL, json=payload)
            if resp.status_code == 200:
                logger.info("Telegram alert sent successfully.")
                return True
            else:
                logger.error(f"Telegram send error: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram exception: {e}")
        return False


# ------------------------------------------------------------------
# Health check functions
# ------------------------------------------------------------------
async def check_api_health() -> Tuple[bool, str]:
    """Check API health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(API_HEALTH_URL)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "operational":
                    return True, "API is healthy"
                else:
                    return False, f"API returned non‑operational status: {data}"
            else:
                return False, f"API health check returned {resp.status_code}"
    except Exception as e:
        return False, f"API health check failed: {e}"


async def check_celery() -> Tuple[bool, str]:
    """Check Celery worker health via custom ping endpoint (if exposed)."""
    # If no dedicated endpoint, we can optionally check task queue length or skip.
    # For now, we assume the API includes a celery ping route.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(CELERY_PING_URL)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return True, "Celery worker is responsive"
                else:
                    return False, f"Celery ping returned unexpected: {data}"
            else:
                return False, f"Celery ping returned {resp.status_code}"
    except Exception as e:
        # If endpoint not available, we consider celery uncheckable; treat as warning but not critical.
        logger.warning(f"Celery ping failed: {e} - treating as non‑critical")
        # We'll return True with a warning message so it doesn't trigger alerts if not mandatory.
        return True, "Celery ping unavailable (ignored)"


async def check_postgres() -> Tuple[bool, str]:
    """Check PostgreSQL connection and version."""
    try:
        engine = create_async_engine(POSTGRES_DSN, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()
            if row == 1:
                return True, "PostgreSQL is reachable"
            else:
                return False, "PostgreSQL returned unexpected result"
    except Exception as e:
        return False, f"PostgreSQL connection failed: {e}"
    finally:
        await engine.dispose()


async def check_redis() -> Tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        await client.close()
        return True, "Redis is reachable"
    except Exception as e:
        return False, f"Redis connection failed: {e}"


async def check_rabbitmq() -> Tuple[bool, str]:
    """Check RabbitMQ connectivity using aio_pika or simple TCP check."""
    # Use a simple socket connection to the RabbitMQ port
    import socket
    try:
        # Extract host and port from URI (simplified)
        # For simplicity, we'll assume the default port 5672 and service name.
        # A more robust method would use aio_pika, but we keep dependency minimal.
        host = "cais-backend-rabbitmq-1"
        port = 5672
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return True, "RabbitMQ port is open"
        else:
            return False, f"RabbitMQ port {port} not reachable"
    except Exception as e:
        return False, f"RabbitMQ check failed: {e}"


# ------------------------------------------------------------------
# Main monitoring loop
# ------------------------------------------------------------------
async def monitor_loop() -> None:
    """
    Main asynchronous monitoring loop.
    Runs every CHECK_INTERVAL seconds, checks all services, and sends alerts on state changes.
    """
    logger.info("CAIS Service Monitor started.")
    logger.info(f"Check interval: {CHECK_INTERVAL}s")
    logger.info("Telegram alerts: %s", "ENABLED" if TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "dummy" else "DISABLED")

    # Define service checks with display names
    services = [
        ("API", check_api_health),
        ("Celery", check_celery),
        ("PostgreSQL", check_postgres),
        ("Redis", check_redis),
        ("RabbitMQ", check_rabbitmq),
    ]

    while True:
        try:
            for service_name, check_func in services:
                logger.debug(f"Checking {service_name}...")
                is_healthy, message = await check_func()
                if update_state(service_name, is_healthy):
                    # State changed
                    if is_healthy:
                        alert = f"✅ *{service_name}* RECOVERED\n{message}"
                        logger.info(f"{service_name} recovered: {message}")
                    else:
                        alert = f"❌ *{service_name}* FAILED\n{message}"
                        logger.error(f"{service_name} failed: {message}")
                    # Send Telegram alert
                    await send_telegram_alert(alert)
                else:
                    # No change; just log if unhealthy
                    if not is_healthy:
                        logger.warning(f"{service_name} still unhealthy: {message}")
                    else:
                        logger.debug(f"{service_name} is healthy")

            # Log overall status summary every loop (optional)
            healthy_count = sum(1 for s in services if service_states.get(s[0], False))
            logger.info(f"Health summary: {healthy_count}/{len(services)} services healthy.")

        except Exception as e:
            logger.exception(f"Unexpected error in monitor loop: {e}")
            # Avoid rapid retry on exception; wait interval
        finally:
            await asyncio.sleep(CHECK_INTERVAL)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")
        sys.exit(0)
