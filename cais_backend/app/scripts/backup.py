"""
Database Backup Script

This script creates a backup of the database.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def backup_database(backup_path: str = None):
    """
    Create a backup of the database.

    Args:
        backup_path: Path to save the backup file
    """
    DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)

    if backup_path is None:
        backup_dir = Path("/app/storage/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"cais_backup_{timestamp}.sql"

    logger.info(f"Creating database backup: {backup_path}")

    try:
        # Parse DATABASE_URL
        import re
        pattern = r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)"
        match = re.match(pattern, DATABASE_URL)

        if match:
            user, password, host, port, database = match.groups()

            # Use pg_dump
            cmd = [
                "pg_dump",
                f"--host={host}",
                f"--port={port}",
                f"--username={user}",
                f"--dbname={database}",
                "--format=plain",
                "--no-owner",
                "--no-privileges"
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = password

            with open(backup_path, "w") as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )

            if result.returncode == 0:
                logger.info(f"Backup created successfully: {backup_path}")
                logger.info(f"File size: {os.path.getsize(backup_path)} bytes")
                return str(backup_path)
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return None
        else:
            logger.error(f"Could not parse DATABASE_URL: {DATABASE_URL}")
            return None

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return None


def list_backups():
    """
    List all available backups.
    """
    backup_dir = Path("/app/storage/backups")
    if not backup_dir.exists():
        logger.info("No backups directory found")
        return []

    backups = sorted(backup_dir.glob("*.sql"), key=os.path.getmtime, reverse=True)
    logger.info(f"Found {len(backups)} backups:")
    for backup in backups:
        size = os.path.getsize(backup) / (1024 * 1024)
        logger.info(f"  {backup.name} ({size:.2f} MB)")
    return backups


if __name__ == "__main__":
    backup_database()
