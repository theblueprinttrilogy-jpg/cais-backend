# app/agents/run_janitor.py - Janitor Agent Execution Script
# Production-ready script that runs the JanitorAgent to archive files older than 45 days
# and safely purge them after uploading to Google Drive under JACINTO_CORREA_COMPUTER.

import os
import sys
import logging
import json
from datetime import datetime

# Add parent directory to path to import JanitorAgent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.janitor_agent import JanitorAgent

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "janitor_run.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger("RunJanitor")

# ------------------------------------------------------------------------------
# Default Directories to Scan
# ------------------------------------------------------------------------------
DEFAULT_DIRECTORIES = [
    "./logs",          # Application logs
    "/tmp",            # Temporary files (be careful with system tmp)
    "./cache",         # Local cache directory
    "./outputs",       # Generated outputs (tarballs, etc.)
    "./artifacts",     # Build artifacts
]

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------
def main():
    logger.info("=" * 80)
    logger.info("C.A.T.S. v2.0 Janitor Agent - 45-Day Sweep")
    logger.info(f"Started at {datetime.utcnow().isoformat()}")
    logger.info("Target Google Drive folder: JACINTO_CORREA_COMPUTER")
    logger.info("=" * 80)

    # Determine directories to scan
    # Allow override via environment variable or command-line arguments? For simplicity, we use default.
    # You can also parse arguments, but we'll keep it simple.
    directories = os.environ.get("JANITOR_DIRECTORIES", "").split(",") if os.environ.get("JANITOR_DIRECTORIES") else DEFAULT_DIRECTORIES
    # Filter out empty strings
    directories = [d.strip() for d in directories if d.strip()]
    logger.info(f"Directories to scan: {directories}")

    # Initialize the JanitorAgent
    try:
        agent = JanitorAgent(
            credentials_file="secrets/credentials.json",
            root_folder_name="JACINTO_CORREA_COMPUTER",
            max_age_days=45
        )
        logger.info("JanitorAgent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize JanitorAgent: {e}")
        sys.exit(1)

    # Run the sweep
    try:
        summary = agent.run_sweep(directories)
        logger.info("Sweep completed. Summary:")
        logger.info(json.dumps(summary, indent=2))

        # Print a human-readable summary
        print("\n" + "=" * 60)
        print("JANITOR SWEEP SUMMARY")
        print("=" * 60)
        print(f"Total directories processed: {summary.get('total_directories', 0)}")
        print(f"Successful archives: {summary.get('successful', 0)}")
        print(f"Fallback (local) archives: {summary.get('fallback', 0)}")
        print(f"Failed: {summary.get('failed', 0)}")
        print(f"Total files archived: {summary.get('total_files_archived', 0)}")
        print(f"Drive file IDs: {summary.get('uploaded_file_ids', [])}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Sweep execution failed: {e}")
        sys.exit(1)

    logger.info("Janitor run finished.")

if __name__ == "__main__":
    main()
