# app/agents/start_janitor_daemon.py - Janitor Daemon for C.A.T.S. v2.0
# Production-ready script that runs the JanitorAgent continuously,
# archiving files older than 45 days to Google Drive under JACINTO_CORREA_COMPUTER.
# Supports graceful shutdown and configurable sweep interval.

import os
import sys
import time
import signal
import logging
import json
from datetime import datetime
from typing import List, Optional

# Add parent directory to path to import JanitorAgent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.janitor_agent import JanitorAgent

# ------------------------------------------------------------------------------
# Configuration (from environment variables with fallbacks)
# ------------------------------------------------------------------------------
SWEEP_INTERVAL = int(os.environ.get("JANITOR_INTERVAL", 3600))  # seconds
DEFAULT_DIRECTORIES = os.environ.get("JANITOR_DIRECTORIES", "./logs,/tmp/out,/cache,/tmp/cais_secure_storage")
DIRECTORIES = [d.strip() for d in DEFAULT_DIRECTORIES.split(",") if d.strip()]
CREDENTIALS_FILE = os.environ.get("JANITOR_CREDENTIALS", "secrets/credentials.json")
ROOT_FOLDER = os.environ.get("JANITOR_ROOT_FOLDER", "JACINTO_CORREA_COMPUTER")

# Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "janitor_daemon.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger("JanitorDaemon")

# ------------------------------------------------------------------------------
# Global flag for graceful shutdown
# ------------------------------------------------------------------------------
_shutdown_requested = False

def signal_handler(sig, frame):
    global _shutdown_requested
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    _shutdown_requested = True

# ------------------------------------------------------------------------------
# Main daemon loop
# ------------------------------------------------------------------------------
def run_daemon():
    global _shutdown_requested

    logger.info("=" * 80)
    logger.info("C.A.T.S. v2.0 Janitor Daemon Starting")
    logger.info(f"Started at {datetime.utcnow().isoformat()}")
    logger.info(f"Target directories: {DIRECTORIES}")
    logger.info(f"Google Drive folder: {ROOT_FOLDER}")
    logger.info(f"Sweep interval: {SWEEP_INTERVAL} seconds")
    logger.info("=" * 80)

    # Initialize JanitorAgent
    try:
        agent = JanitorAgent(
            credentials_file=CREDENTIALS_FILE,
            root_folder_name=ROOT_FOLDER,
            max_age_days=45
        )
        logger.info("JanitorAgent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize JanitorAgent: {e}")
        sys.exit(1)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    while not _shutdown_requested:
        try:
            logger.info("Starting sweep cycle...")
            summary = agent.run_sweep(DIRECTORIES)
            logger.info("Sweep cycle completed. Summary:")
            logger.info(json.dumps(summary, indent=2))
            logger.info(f"Sleeping for {SWEEP_INTERVAL} seconds until next sweep.")
            # Sleep in small increments to check shutdown flag more often
            sleep_remaining = SWEEP_INTERVAL
            while sleep_remaining > 0 and not _shutdown_requested:
                time.sleep(min(1.0, sleep_remaining))
                sleep_remaining -= 1.0
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            break
        except Exception as e:
            logger.error(f"Unhandled error in sweep cycle: {e}")
            # Wait a bit before retrying to avoid tight loops
            time.sleep(10)

    # Graceful shutdown
    logger.info("Shutting down Janitor daemon...")
    agent.reset_tracking()  # optional cleanup
    logger.info("Janitor daemon stopped.")

# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    run_daemon()
