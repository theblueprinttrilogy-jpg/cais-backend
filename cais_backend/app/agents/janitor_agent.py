"""
Janitor Agent – Responsible for cleaning up temporary files, logs, caches,
and archiving unrelated or stale files to Google Drive.

Deterministic relevance engine classifies files as CORE CAIS artifacts or
non‑core based on directory structure, naming conventions, and age.

All paths are container‑native; configuration via environment variables.
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Tuple

from app.services.drive import GoogleDriveUploader  # Assuming a service module exists

logger = logging.getLogger(__name__)


class JanitorAgent:
    """
    Janitor Agent for CAIS Code Compliance.

    Responsibilities:
        - Determine if a file is a core CAIS artifact (deterministic rules).
        - Archive unrelated or old (exceeding max_age) files to Google Drive.
        - Delete archived files locally after successful upload.
    """

    # Core directories that are considered part of CAIS codebase
    CORE_DIRS = {
        "app/core",
        "app/agents",
        "app/api",
        "app/workers",
        "tests",
        "api",
        "core",
    }

    # Keywords that indicate a file is CAIS‑related (in path or name)
    CAIS_KEYWORDS = {
        "cais",
        "compliance",
        "building_code",
    }

    # Temporary / cache / log directories that are typically non‑core
    NONCORE_DIRS = {
        "/tmp",
        "/app/tmp",
        "/app/logs",
        "/app/cache",
        "/app/data/temp",
        "/app/data/cache",
        "/app/data/logs",
    }

    def __init__(
        self,
        temp_dir: str = "/app/data/temp",
        data_dir: str = "/app/data",
        max_age_days: int = 45,
        drive_root_folder: str = "JACINTO_CORREA_COMPUTER",
        uploader: Optional[GoogleDriveUploader] = None,
    ):
        """
        Initialize the JanitorAgent.

        Args:
            temp_dir: Path to temporary directory (used for local operations).
            data_dir: Base data directory for the application.
            max_age_days: Files older than this (in days) are candidates for archiving.
            drive_root_folder: Root folder name in Google Drive for archived files.
            uploader: Instance of GoogleDriveUploader; if None, a new one is created.
        """
        self.temp_dir = Path(temp_dir)
        self.data_dir = Path(data_dir)
        self.max_age_days = max_age_days
        self.drive_root_folder = drive_root_folder

        # Ensure the uploader is available
        if uploader is None:
            self.uploader = GoogleDriveUploader()
        else:
            self.uploader = uploader

        logger.info(
            f"JanitorAgent initialized: temp_dir={temp_dir}, max_age={max_age_days}d, "
            f"drive_root='{drive_root_folder}'"
        )

    def is_related_to_cais(self, file_path: str, content_snippet: Optional[str] = None) -> bool:
        """
        Deterministically evaluate whether a file belongs to CAIS Code Compliance.

        Rules (in order):
            1. If the file resides in any CORE_DIRS → return True.
            2. If the file path or name contains any CAIS_KEYWORDS → return True.
            3. Otherwise → return False (non‑core).

        The 'content_snippet' is currently ignored but kept for future extension
        (e.g., scanning file content for CAIS terms).

        Args:
            file_path: Absolute or relative path to the file.
            content_snippet: Optional first few lines of file content (unused).

        Returns:
            True if the file is considered a CAIS core artifact, False otherwise.
        """
        path = Path(file_path)
        path_str = str(path).lower().replace("\\", "/")  # normalize
        name_lower = path.name.lower()

        # Rule 1: Check if path belongs to any core directory
        # We check if the path starts with or contains the core dir segment
        for core_dir in self.CORE_DIRS:
            # Normalize core_dir to use forward slashes
            normalized_core = core_dir.replace("\\", "/").lower()
            # Check if the core_dir is a prefix of the relative path
            # We need to get the relative path from root? Simpler: check if normalized_core in path_str
            # But to be safe, we check if the path contains the core dir as a segment.
            # We'll split by '/' and check if any segment matches core_dir exactly.
            parts = path_str.split("/")
            # Also allow partial matches? We'll check if the core_dir is a subpath.
            if normalized_core in path_str:
                logger.debug(f"File '{file_path}' is in core directory '{core_dir}'")
                return True

        # Rule 2: Check path or name for CAIS keywords
        for keyword in self.CAIS_KEYWORDS:
            if keyword in path_str or keyword in name_lower:
                logger.debug(f"File '{file_path}' contains CAIS keyword '{keyword}'")
                return True

        # Rule 3: Not core and no keywords → non‑core
        return False

    async def _upload_to_drive(self, file_path: Path) -> bool:
        """
        Upload a file to Google Drive under the root folder 'JACINTO_CORREA_COMPUTER'.

        Returns True on success, False on failure.
        """
        try:
            # Ensure the file exists
            if not file_path.is_file():
                logger.error(f"File {file_path} does not exist, cannot upload.")
                return False

            # Use the uploader to upload the file
            # The uploader's upload_file method should accept a path and return success.
            # We assume it returns a file ID or raises an exception.
            # We'll wrap in try/except.
            logger.info(f"Uploading file to Drive: {file_path}")
            # Create a subfolder structure based on date? For simplicity, upload to root.
            # We'll use the uploader's upload_file method.
            result = self.uploader.upload_file(str(file_path))
            # If result is a file ID, success.
            if result:
                logger.info(f"Successfully uploaded {file_path} to Drive.")
                return True
            else:
                logger.error(f"Upload failed for {file_path} (no file ID returned).")
                return False
        except Exception as e:
            logger.exception(f"Exception during upload of {file_path}: {e}")
            return False

    async def _archive_and_cleanup(self, file_path: Path) -> None:
        """
        Archive a file to Google Drive and delete it locally if upload succeeds.

        If upload fails, the file is kept locally and an error is logged.
        """
        if not file_path.is_file():
            logger.warning(f"File {file_path} does not exist, skipping.")
            return

        # Upload to Drive
        success = await self._upload_to_drive(file_path)
        if success:
            try:
                file_path.unlink()
                logger.info(f"Deleted local file after archiving: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete local file {file_path}: {e}")
        else:
            logger.error(f"Failed to archive {file_path}; keeping local file.")

    async def run_sweep(self) -> None:
        """
        Perform a full sweep: traverse directories, evaluate relevance, and archive old/unrelated files.

        The sweep examines files in:
            - The temporary directory (temp_dir)
            - The logs directory (if exists: data_dir/logs)
            - The cache directory (if exists: data_dir/cache)
            - Any directory that is non‑core and not explicitly allowed.

        For each file found:
            - If it is a core CAIS file (is_related_to_cais() == True) → skip.
            - Else if the file is older than max_age_days → archive to Drive and delete local.
            - Else (not core, but not old enough) → leave it (may be a recent non‑core file).
        """
        logger.info("Starting Janitor sweep...")

        # Collect directories to scan
        dirs_to_scan: List[Path] = []
        # Add explicit directories
        for dir_path in [self.temp_dir, self.data_dir / "logs", self.data_dir / "cache"]:
            if dir_path.exists() and dir_path.is_dir():
                dirs_to_scan.append(dir_path)

        # If the data_dir itself is not core, we might scan it, but we'll limit to avoid
        # scanning everything. We'll only scan subdirectories that are explicitly non-core.
        # Actually, we'll scan all files in the entire data_dir, but we'll skip any that
        # are in core directories or contain CAIS keywords.
        # We'll also scan the entire /app directory? We'll stick to data_dir, logs, cache, temp.
        # Also we might scan /app/root for stray scripts? For safety, we'll scan /app except core dirs.
        # To keep it manageable, we'll scan the following base paths:
        base_paths = [
            self.temp_dir,
            self.data_dir / "logs",
            self.data_dir / "cache",
        ]
        # Also scan the root of the project for arbitrary scripts? We'll skip to avoid deleting critical files.
        # We'll assume that any file outside core dirs and without keywords is non-core, but we only archive if old.

        # We'll recursively walk each base path
        for base in base_paths:
            if not base.exists():
                continue
            # Walk the directory tree
            for root, dirs, files in base.walk():
                for file_name in files:
                    file_path = root / file_name
                    try:
                        # Check if it's a file (skip symlinks, etc.)
                        if not file_path.is_file():
                            continue

                        # Evaluate relevance
                        if self.is_related_to_cais(str(file_path)):
                            logger.debug(f"Skipping core file: {file_path}")
                            continue

                        # Check age
                        try:
                            mtime = file_path.stat().st_mtime
                            age = (datetime.now() - datetime.fromtimestamp(mtime)).days
                        except Exception as e:
                            logger.warning(f"Could not get age for {file_path}: {e}")
                            continue

                        if age >= self.max_age_days:
                            logger.info(f"Archiving old non-core file: {file_path} (age={age}d)")
                            await self._archive_and_cleanup(file_path)
                        else:
                            logger.debug(f"Non-core file is recent, keeping: {file_path} (age={age}d)")

                    except Exception as e:
                        logger.exception(f"Error processing file {file_path}: {e}")

        logger.info("Janitor sweep completed.")
