import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.services.drive import GoogleDriveService  # Assume this exists

logger = logging.getLogger(__name__)


class JanitorService:
    """
    Service responsible for cleaning up stale or orphaned files.
    This includes permanently deleting files that have been soft-deleted
    for longer than a retention period, and removing their associated
    Google Drive files.
    """

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

    async def run_cleanup(self) -> int:
        """
        Execute the full cleanup routine.

        :return: Number of files permanently deleted.
        """
        logger.info("Starting janitor cleanup cycle")
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        # Find files that have been soft-deleted and exceeded retention
        files_to_purge = await self._find_expired_files(cutoff_date)
        if not files_to_purge:
            logger.info("No expired files to purge")
            return 0

        logger.info(f"Found {len(files_to_purge)} files to purge")

        deleted_count = 0
        for file in files_to_purge:
            try:
                await self._purge_file(file)
                deleted_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to purge file {file.id}: {e}",
                    exc_info=True,
                )
                # Continue with next file; do not roll back entire batch

        logger.info(f"Janitor cleanup completed. Deleted {deleted_count} files")
        return deleted_count

    async def _find_expired_files(self, cutoff_date: datetime) -> List[File]:
        """
        Query the database for files that are soft-deleted and older than cutoff.

        :param cutoff_date: Files with deleted_at < this date will be selected.
        :return: List of File instances.
        """
        stmt = select(File).where(
            File.deleted_at.is_not(None),
            File.deleted_at < cutoff_date,
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def _purge_file(self, file: File) -> None:
        """
        Permanently delete a single file and its Google Drive counterpart.

        This method runs the Google Drive deletion in a separate thread to
        avoid blocking the async event loop.

        :param file: The File instance to purge.
        """
        # Delete from Google Drive first (if applicable)
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

    async def run_orphan_cleanup(self) -> int:
        """
        Clean up files that have no associated parent record (orphans).

        This is a separate routine for files that were never soft-deleted
        but whose parent entity no longer exists.

        :return: Number of orphan files permanently deleted.
        """
        logger.info("Starting orphan cleanup")
        # This is a placeholder; actual orphan detection logic depends on
        # your schema. For example, if File has a foreign key to a parent
        # that might be null or missing.
        # We assume there is a method to find orphans.
        orphan_files = await self._find_orphan_files()
        if not orphan_files:
            logger.info("No orphan files found")
            return 0

        deleted_count = 0
        for file in orphan_files:
            try:
                await self._purge_file(file)
                deleted_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to purge orphan file {file.id}: {e}",
                    exc_info=True,
                )

        logger.info(f"Orphan cleanup completed. Deleted {deleted_count} files")
        return deleted_count

    async def _find_orphan_files(self) -> List[File]:
        """
        Find files that have no parent object referencing them.

        This is a stub; implement according to your data model.

        :return: List of File instances considered orphans.
        """
        # Example: files whose parent_id is not found in the parent table.
        # You would need to adjust the query based on your actual schema.
        # For demonstration, we return an empty list.
        return []

    async def close(self) -> None:
        """
        Clean up resources if needed.
        """
        # If the session is managed externally, do not close it here.
        # This method is a no-op by default; override if needed.
        pass
