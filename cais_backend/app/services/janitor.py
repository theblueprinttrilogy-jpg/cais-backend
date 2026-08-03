import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.services.drive import GoogleDriveService

logger = logging.getLogger(__name__)


class JanitorService:
    """
    Service responsible for cleaning up stale or orphaned files.
    Includes disk-space awareness to trigger aggressive purges when
    free space falls below a healthy threshold.
    """

    # Healthy free space threshold (20% of total disk space)
    HEALTHY_THRESHOLD = 0.20

    # Directories to clean for temporary caches and logs
    TEMP_CACHE_DIRS = [
        "/tmp/cais_cache",
        "/var/cache/cais",
    ]
    LOG_DIRS = [
        "/var/log/cais",
        "/app/logs",
    ]

    def __init__(
        self,
        db_session: AsyncSession,
        drive_service: GoogleDriveService,
        retention_days: int = 30,
    ) -> None:
        """
        Initialize the janitor service.

        :param db_session: Async SQLAlchemy session for database operations.
        :param drive_service: Service for interacting with Google Drive.
        :param retention_days: Number of days to retain soft-deleted files
                               before permanent deletion.
        """
        self.db_session = db_session
        self.drive_service = drive_service
        self.retention_days = retention_days

    def _get_disk_usage(self) -> Tuple[int, int, int]:
        """
        Synchronous helper to get disk usage statistics.

        :return: Tuple of (total_bytes, used_bytes, free_bytes).
        """
        usage = shutil.disk_usage("/")
        return usage.total, usage.used, usage.free

    async def get_disk_usage_async(self) -> Dict[str, Any]:
        """
        Asynchronously retrieve disk usage statistics.

        :return: Dictionary with total, used, free (in bytes) and free_percent.
        """
        total, used, free = await asyncio.to_thread(self._get_disk_usage)
        free_percent = free / total if total > 0 else 0.0
        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_percent": free_percent,
        }

    async def _is_disk_critical(self) -> bool:
        """
        Determine if free disk space is below the healthy threshold.

        :return: True if critical, False otherwise.
        """
        stats = await self.get_disk_usage_async()
        return stats["free_percent"] < self.HEALTHY_THRESHOLD

    async def _purge_temp_cache(self) -> int:
        """
        Purge temporary cache directories.

        :return: Number of files/directories removed.
        """
        removed_count = 0
        for dir_path in self.TEMP_CACHE_DIRS:
            if os.path.exists(dir_path):
                try:
                    # Use shutil.rmtree in a thread to avoid blocking
                    await asyncio.to_thread(shutil.rmtree, dir_path, ignore_errors=True)
                    removed_count += 1
                    logger.info(f"Purged temporary cache directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Failed to purge temp cache {dir_path}: {e}")
        return removed_count

    async def _purge_logs(self) -> int:
        """
        Purge old log files (keeping only recent ones).

        :return: Number of log files removed.
        """
        removed_count = 0
        for log_dir in self.LOG_DIRS:
            if os.path.exists(log_dir):
                try:
                    # List files in log directory and remove those older than 7 days
                    # This is a simple implementation; can be enhanced.
                    files = await asyncio.to_thread(os.listdir, log_dir)
                    cutoff = datetime.utcnow() - timedelta(days=7)
                    for filename in files:
                        file_path = os.path.join(log_dir, filename)
                        if os.path.isfile(file_path):
                            stat = await asyncio.to_thread(os.stat, file_path)
                            mtime = datetime.utcfromtimestamp(stat.st_mtime)
                            if mtime < cutoff:
                                await asyncio.to_thread(os.remove, file_path)
                                removed_count += 1
                                logger.debug(f"Removed old log file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to purge logs from {log_dir}: {e}")
        return removed_count

    async def _purge_eligible_files(
        self,
        cutoff_date: datetime,
        limit: Optional[int] = None,
    ) -> int:
        """
        Purge soft-deleted files older than cutoff_date.

        :param cutoff_date: Files with deleted_at < this date are eligible.
        :param limit: Optional maximum number of files to purge.
        :return: Number of files purged.
        """
        stmt = select(File).where(
            File.deleted_at.is_not(None),
            File.deleted_at < cutoff_date,
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db_session.execute(stmt)
        files = result.scalars().all()

        purged = 0
        for file in files:
            try:
                await self._purge_file(file)
                purged += 1
            except Exception as e:
                logger.error(f"Failed to purge file {file.id}: {e}", exc_info=True)
        return purged

    async def _purge_file(self, file: File) -> None:
        """
        Permanently delete a single file and its Google Drive counterpart.

        :param file: The File instance to purge.
        """
        if file.google_drive_file_id:
            logger.debug(f"Deleting Google Drive file {file.google_drive_file_id}")
            await asyncio.to_thread(
                self.drive_service.delete_file,
                file.google_drive_file_id,
            )

        # Remove the file record from the database
        logger.debug(f"Deleting file record {file.id}")
        stmt = update(File).where(File.id == file.id).values(
            permanently_deleted_at=datetime.utcnow(),
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def run_cleanup(
        self,
        aggressive: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the janitor cleanup cycle with disk-space awareness.

        If free space is below the healthy threshold, an aggressive purge
        is triggered: it purges expired files regardless of retention,
        clears temporary caches, and prunes logs until space is healthy
        or no more items can be removed.

        :param aggressive: If True, force aggressive mode regardless of disk state.
        :return: Detailed metrics dictionary containing:
                 - purged_files: total files permanently deleted
                 - free_space_before: free bytes before cleanup
                 - free_space_after: free bytes after cleanup
                 - is_healthy: True if free space is above threshold after cleanup
                 - additional_cleanups: dict with counts for temp_cache and logs
        """
        logger.info("Starting janitor cleanup cycle")

        # Get disk usage before cleanup
        stats_before = await self.get_disk_usage_async()
        free_before = stats_before["free_bytes"]

        # Determine if we need aggressive cleanup
        is_critical = stats_before["free_percent"] < self.HEALTHY_THRESHOLD
        if is_critical or aggressive:
            logger.warning(
                f"Disk space critical: {stats_before['free_percent']:.2%} free. "
                "Initiating aggressive purge."
            )
            return await self._run_aggressive_cleanup(free_before)

        # Normal cleanup: only expired files based on retention
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        purged_files = await self._purge_eligible_files(cutoff_date)

        # After normal cleanup, check disk again
        stats_after = await self.get_disk_usage_async()
        free_after = stats_after["free_bytes"]
        is_healthy = stats_after["free_percent"] >= self.HEALTHY_THRESHOLD

        logger.info(f"Normal cleanup completed. Purged {purged_files} files.")
        return {
            "purged_files": purged_files,
            "free_space_before": free_before,
            "free_space_after": free_after,
            "is_healthy": is_healthy,
            "additional_cleanups": {
                "temp_cache": 0,
                "logs": 0,
            },
        }

    async def _run_aggressive_cleanup(
        self,
        free_before: int,
    ) -> Dict[str, Any]:
        """
        Perform aggressive cleanup to restore disk health.

        This method repeatedly purges files and additional caches/logs
        until free space is above the healthy threshold or no more items
        can be removed.

        :param free_before: Free bytes before any cleanup.
        :return: Metrics dictionary with additional cleanups.
        """
        total_purged_files = 0
        temp_cleaned = 0
        logs_cleaned = 0

        # First, purge all expired files regardless of age (use a very old cutoff)
        # We'll use a cutoff date far in the past to include all soft-deleted files.
        # Alternatively, we can purge all soft-deleted files, not just old ones.
        # We'll do: all soft-deleted files (deleted_at is not None)
        stmt = select(File).where(File.deleted_at.is_not(None))
        result = await self.db_session.execute(stmt)
        all_deleted = result.scalars().all()
        for file in all_deleted:
            try:
                await self._purge_file(file)
                total_purged_files += 1
            except Exception as e:
                logger.error(f"Failed to purge file {file.id}: {e}")

        # After purging soft-deleted files, check if we need more
        stats_after_files = await self.get_disk_usage_async()
        if stats_after_files["free_percent"] >= self.HEALTHY_THRESHOLD:
            # Already healthy, no need to clean caches/logs
            return {
                "purged_files": total_purged_files,
                "free_space_before": free_before,
                "free_space_after": stats_after_files["free_bytes"],
                "is_healthy": True,
                "additional_cleanups": {
                    "temp_cache": 0,
                    "logs": 0,
                },
            }

        # Now clean temporary caches
        temp_cleaned = await self._purge_temp_cache()

        # Check again
        stats_after_temp = await self.get_disk_usage_async()
        if stats_after_temp["free_percent"] >= self.HEALTHY_THRESHOLD:
            return {
                "purged_files": total_purged_files,
                "free_space_before": free_before,
                "free_space_after": stats_after_temp["free_bytes"],
                "is_healthy": True,
                "additional_cleanups": {
                    "temp_cache": temp_cleaned,
                    "logs": 0,
                },
            }

        # Finally, purge logs
        logs_cleaned = await self._purge_logs()

        # Final check
        stats_final = await self.get_disk_usage_async()
        is_healthy = stats_final["free_percent"] >= self.HEALTHY_THRESHOLD

        logger.info(
            f"Aggressive cleanup completed. Purged files: {total_purged_files}, "
            f"temp cache: {temp_cleaned}, logs: {logs_cleaned}. "
            f"Healthy: {is_healthy}"
        )

        return {
            "purged_files": total_purged_files,
            "free_space_before": free_before,
            "free_space_after": stats_final["free_bytes"],
            "is_healthy": is_healthy,
            "additional_cleanups": {
                "temp_cache": temp_cleaned,
                "logs": logs_cleaned,
            },
        }

    async def run_orphan_cleanup(self) -> int:
        """
        Clean up files that have no associated parent record (orphans).

        :return: Number of orphan files permanently deleted.
        """
        logger.info("Starting orphan cleanup")
        # Placeholder - implement based on your schema.
        return 0

    async def close(self) -> None:
        """
        Clean up resources if needed.
        """
        pass
