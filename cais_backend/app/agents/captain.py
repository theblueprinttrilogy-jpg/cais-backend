#!/usr/bin/env python3
"""
captain.py - Consumes Redis queue and launches search agents.
"""

import os, sys, json, time, signal, logging, subprocess
from multiprocessing import Pool
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "cais-backend-redis-1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
QUEUE_KEY = "cais:jurisdictions:queue"
MAX_AGENTS = 3
CAPTAIN_ID = os.environ.get("CAPTAIN_ID", "1")
LOG_FILE = f"/app/logs/captains/captain_{CAPTAIN_ID}.out"

try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    r.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    sys.exit(1)

def run_agent(jurisdiction_data):
    try:
        j = json.dumps(jurisdiction_data)
        logger.info(f"Launching agent for {jurisdiction_data.get('name', 'unknown')}")
        result = subprocess.run(
            [sys.executable, '/app/agents/search_agent.py', j],
            capture_output=True, text=True, timeout=600
        )
        return {"jurisdiction": jurisdiction_data, "success": result.returncode == 0}
    except Exception as e:
        return {"jurisdiction": jurisdiction_data, "success": False, "error": str(e)}

def main():
    logger.info(f"Captain {CAPTAIN_ID} started. Max agents: {MAX_AGENTS}")
    pool = Pool(processes=MAX_AGENTS)
    running = True
    def signal_handler(sig, frame):
        nonlocal running
        running = False
        pool.terminate()
        pool.join()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        try:
            j = r.brpoplpush(QUEUE_KEY, f"{QUEUE_KEY}:processing", timeout=5)
            if j is None:
                time.sleep(1)
                continue
            try:
                data = json.loads(j)
                logger.info(f"Processing: {data}")
                pool.apply_async(run_agent, (data,))
            except json.JSONDecodeError:
                r.lpush("cais:jurisdictions:dlq", j)
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
