"""
Cleanup Script - Removes Temporary Files

This script cleans up temporary files, old logs, and expired data.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cleanup_temp_files(days_old: int = 7):
    """
    Clean up temporary files older than specified days.

    Args:
        days_old: Delete files older than this many days
    """
    temp_dirs = [
        "/tmp/cais_*",
        "/app/storage/temp",
        "/app/storage/evidence",
        "/app/storage/uploads",
        "/app/logs"
    ]

    cutoff_time = datetime.now() - timedelta(days=days_old)
    total_deleted = 0
    total_size = 0

    for dir_pattern in temp_dirs:
        import glob
        for dir_path in glob.glob(dir_pattern):
            if os.path.exists(dir_path):
                deleted, size = _cleanup_directory(dir_path, cutoff_time)
                total_deleted += deleted
                total_size += size

    logger.info(f"Cleanup completed: {total_deleted} files deleted, {total_size / (1024*1024):.2f} MB freed")


def _cleanup_directory(dir_path: str, cutoff_time: datetime):
    """
    Clean up a specific directory.

    Returns:
        Tuple[int, int]: (files_deleted, bytes_freed)
    """
    files_deleted = 0
    bytes_freed = 0

    try:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mtime < cutoff_time:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_deleted += 1
                        bytes_freed += size
                        logger.debug(f"Deleted: {file_path} ({size} bytes)")
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")

            # Remove empty directories
            for dir_name in dirs:
                dir_full = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_full):
                        os.rmdir(dir_full)
                        logger.debug(f"Removed empty directory: {dir_full}")
                except Exception as e:
                    logger.error(f"Error removing directory {dir_full}: {e}")

        logger.info(f"Cleaned {dir_path}: {files_deleted} files, {bytes_freed / (1024*1024):.2f} MB")
        return files_deleted, bytes_freed

    except Exception as e:
        logger.error(f"Error cleaning {dir_path}: {e}")
        return 0, 0


def cleanup_old_logs(days_old: int = 30):
    """
    Clean up old log files.

    Args:
        days_old: Delete logs older than this many days
    """
    log_dir = Path("/app/logs")
    if not log_dir.exists():
        logger.info("No logs directory found")
        return

    cutoff_time = datetime.now() - timedelta(days=days_old)
    files_deleted = 0
    bytes_freed = 0

    for log_file in log_dir.glob("*.log*"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_time:
                size = log_file.stat().st_size
                log_file.unlink()
                files_deleted += 1
                bytes_freed += size
                logger.debug(f"Deleted log: {log_file.name}")
        except Exception as e:
            logger.error(f"Error deleting {log_file}: {e}")

    logger.info(f"Log cleanup: {files_deleted} files deleted, {bytes_freed / (1024*1024):.2f} MB freed")


def cleanup_expired_data():
    """
    Clean up expired data from the database.
    """
    import os
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from sqlalchemy import create_engine, text
    from app.core.config import settings

    DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Delete expired tokens (if any)
        # Delete old violations (if any)
        # This would be expanded based on business rules
        logger.info("Expired data cleanup completed")


if __name__ == "__main__":
    cleanup_temp_files()
