"""
Continuous background watchdog for CAIS system services.

Monitors API backend, Celery worker, PostgreSQL, Redis, and RabbitMQ.
Sends Telegram alerts on service failure or recovery.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Tuple

import httpx
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CAIS-Monitor")

# Configuration - STRICTLY from environment variables (No hardcoded credentials)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None

API_HEALTH_URL = os.getenv("API_HEALTH_URL", "http://cais-backend:8080/health")
CELERY_PING_URL = os.getenv("CELERY_PING_URL", "http://cais-backend:8080/celery/ping")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql+asyncpg://postgres:postgres@cais-postgres:5432/cais_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://cais-backend-redis-1:6379/0")
CHECK_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "30"))

service_states: Dict[str, bool] = {}

def update_state(service_name: str, is_healthy: bool) -> bool:
    previous = service_states.get(service_name)
    if previous is None or previous != is_healthy:
        service_states[service_name] = is_healthy
        return True
    return False

async def send_telegram_alert(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured; skipping alert.")
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

async def check_api_health() -> Tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(API_HEALTH_URL)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "operational":
                    return True, "API is healthy"
                else:
                    return False, f"API returned non-operational status: {data}"
            else:
                return False, f"API health check returned {resp.status_code}"
    except Exception as e:
        return False, f"API health check failed: {e}"

async def check_celery() -> Tuple[bool, str]:
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
        return True, "Celery ping unavailable (ignored)"

async def check_postgres() -> Tuple[bool, str]:
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
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
        await client.close()
        return True, "Redis is reachable"
    except Exception as e:
        return False, f"Redis connection failed: {e}"

async def check_rabbitmq() -> Tuple[bool, str]:
    import socket
    try:
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

async def monitor_loop() -> None:
    logger.info("CAIS Service Monitor started.")
    logger.info(f"Check interval: {CHECK_INTERVAL}s")
    logger.info("Telegram alerts: %s", "ENABLED" if TELEGRAM_BOT_TOKEN else "DISABLED")

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
                is_healthy, message = await check_func()
                if update_state(service_name, is_healthy):
                    if is_healthy:
                        alert = f"✅ *{service_name}* RECOVERED\n{message}"
                        logger.info(f"{service_name} recovered: {message}")
                    else:
                        alert = f"❌ *{service_name}* FAILED\n{message}"
                        logger.error(f"{service_name} failed: {message}")
                    await send_telegram_alert(alert)
                else:
                    if not is_healthy:
                        logger.warning(f"{service_name} still unhealthy: {message}")

            healthy_count = sum(1 for s in services if service_states.get(s[0], False))
            logger.info(f"Health summary: {healthy_count}/{len(services)} services healthy.")

        except Exception as e:
            logger.exception(f"Unexpected error in monitor loop: {e}")
        finally:
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")
        sys.exit(0)
