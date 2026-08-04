"""
app/agents/dictionary_drive_archiver.py

Dual-Account Google Drive Archiver Agent with Automatic Failover and Compression.

This agent:
1. Compresses raw dictionary files from /tmp/cais_dictionaries/raw into a structured
   .zip archive, organized by language/domain.
2. Uploads the archive to a primary Google Drive account (jc.duvalmasterconstruction@gmail.com).
3. If the primary upload fails (quota, auth, network), automatically fails over to a
   backup account (jcf.lagaresconstruction@gmail.com).
4. Returns detailed telemetry for each operation.

Provides a clean CLI interface with comprehensive logging.
"""

import argparse
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Configure logging
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_RAW_DIR = "/tmp/cais_dictionaries/raw"
DEFAULT_ARCHIVE_DIR = "/tmp/cais_dictionaries"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class DriveUploader:
    """
    Helper class to handle uploads to a single Google Drive account.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        folder_id: Optional[str] = None,
    ):
        """
        Initialize a Drive uploader for a specific account.

        :param client_id: OAuth2 client ID.
        :param client_secret: OAuth2 client secret.
        :param refresh_token: OAuth2 refresh token.
        :param folder_id: Optional folder ID to upload to (if None, uploads to root).
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.folder_id = folder_id
        self._service = None
        self._account_label = "unknown"

    @property
    def service(self):
        """Lazy initialize the Drive service."""
        if self._service is None:
            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                client_id=self.client_id,
                client_secret=self.client_secret,
                token_uri=TOKEN_URI,
                scopes=["https://www.googleapis.com/auth/drive"],
            )
            self._service = build("drive", "v3", credentials=creds)
            logger.debug("Drive service initialized.")
        return self._service

    def upload_file(self, file_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a single file to this account's folder.

        :param file_path: Path to the local file.
        :param file_name: Optional name in Drive (defaults to basename).
        :return: Telemetry dict.
        :raises: HttpError or other exceptions.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = file_name or os.path.basename(file_path)
        file_metadata = {"name": file_name}
        if self.folder_id:
            file_metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(file_path, resumable=True)

        result = (
            self.service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, size",
                supportsAllDrives=True,
            )
            .execute()
        )
        return {
            "status": "success",
            "file_id": result.get("id"),
            "name": result.get("name"),
            "web_view_link": result.get("webViewLink"),
            "size": result.get("size"),
            "timestamp": datetime.utcnow().isoformat(),
        }


class DictionaryDriveArchiverAgent:
    """
    Dual-account archiver with compression, categorization, and automatic failover.
    """

    def __init__(
        self,
        primary_client_id: str,
        primary_client_secret: str,
        primary_refresh_token: str,
        primary_folder_id: Optional[str] = None,
        backup_client_id: Optional[str] = None,
        backup_client_secret: Optional[str] = None,
        backup_refresh_token: Optional[str] = None,
        backup_folder_id: Optional[str] = None,
        raw_dir: str = DEFAULT_RAW_DIR,
        archive_dir: str = DEFAULT_ARCHIVE_DIR,
    ):
        """
        Initialize the archiver with primary and backup credentials.

        :param primary_client_id: Primary OAuth2 client ID.
        :param primary_client_secret: Primary OAuth2 client secret.
        :param primary_refresh_token: Primary OAuth2 refresh token.
        :param primary_folder_id: Primary folder ID (optional).
        :param backup_client_id: Backup OAuth2 client ID (optional).
        :param backup_client_secret: Backup OAuth2 client secret (optional).
        :param backup_refresh_token: Backup OAuth2 refresh token (optional).
        :param backup_folder_id: Backup folder ID (optional).
        :param raw_dir: Directory containing raw dictionary files to compress.
        :param archive_dir: Directory to store the generated .zip archive.
        """
        self.primary = DriveUploader(
            client_id=primary_client_id,
            client_secret=primary_client_secret,
            refresh_token=primary_refresh_token,
            folder_id=primary_folder_id,
        )
        self.primary._account_label = "primary"

        self.backup = None
        if backup_client_id and backup_client_secret and backup_refresh_token:
            self.backup = DriveUploader(
                client_id=backup_client_id,
                client_secret=backup_client_secret,
                refresh_token=backup_refresh_token,
                folder_id=backup_folder_id,
            )
            self.backup._account_label = "backup"
        else:
            logger.info("Backup credentials not provided; failover disabled.")

        self.raw_dir = Path(raw_dir)
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Compression and categorization
    # ------------------------------------------------------------------
    def _categorize_raw_files(self) -> Dict[str, List[Path]]:
        """
        Scan raw_dir and group files by language/domain based on filename patterns.
        Returns a dict mapping category (language) to list of file paths.
        """
        if not self.raw_dir.exists():
            logger.warning(f"Raw directory does not exist: {self.raw_dir}")
            return {}

        categories = {}
        # Try to infer language from filename: assume language code at start, e.g., "en_osha_standards.json"
        for file_path in self.raw_dir.iterdir():
            if file_path.is_file():
                # Simple heuristic: split by underscore; first token may be language code
                parts = file_path.stem.split("_")
                if parts:
                    # If first part is a known language code (en, es, zh, etc.) use it
                    known_langs = {"en", "es", "zh", "pt", "fr", "de", "ja", "ar", "hi", "id", "ru"}
                    lang = parts[0].lower() if parts[0].lower() in known_langs else "other"
                    categories.setdefault(lang, []).append(file_path)
                else:
                    categories.setdefault("other", []).append(file_path)

        # Log categorization
        for lang, files in categories.items():
            logger.info(f"Category '{lang}': {len(files)} files")
        return categories

    def _create_archive(self, categories: Dict[str, List[Path]]) -> str:
        """
        Create a .zip archive from categorized files.
        Returns the path to the created archive.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"dictionary_archive_{timestamp}.zip"
        archive_path = self.archive_dir / archive_name

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for category, files in categories.items():
                # Create a folder inside the zip for each category
                for file_path in files:
                    # Store with path: category/filename
                    arcname = f"{category}/{file_path.name}"
                    zf.write(file_path, arcname)

        logger.info(f"Created archive: {archive_path} (size: {archive_path.stat().st_size} bytes)")
        return str(archive_path)

    # ------------------------------------------------------------------
    # Upload with failover
    # ------------------------------------------------------------------
    def _upload_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Attempt to upload a single file using primary account; on failure, failover to backup.
        """
        base_result = {
            "file": file_path,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Try primary
            logger.info(f"Uploading {file_path} to Primary Drive...")
            result = self.primary.upload_file(file_path)
            result["account"] = "primary"
            result["failover"] = False
            logger.info(f"Primary upload successful: {result.get('file_id')}")
            return {**base_result, **result}
        except Exception as e:
            logger.warning(f"Primary upload failed: {e}")

            # Check if backup is available
            if self.backup is None:
                logger.error("Backup account not configured. Upload failed.")
                return {
                    **base_result,
                    "status": "failed",
                    "account": "primary",
                    "error": str(e),
                    "failover_attempted": False,
                }

            # Attempt backup
            logger.info(f"Failing over to Backup Drive for {file_path}...")
            try:
                result = self.backup.upload_file(file_path)
                result["account"] = "backup"
                result["failover"] = True
                logger.info(f"Backup upload successful: {result.get('file_id')}")
                return {**base_result, **result}
            except Exception as backup_e:
                logger.error(f"Backup upload also failed: {backup_e}")
                return {
                    **base_result,
                    "status": "failed",
                    "account": "backup",
                    "error": str(backup_e),
                    "failover_attempted": True,
                }

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------
    def run(
        self,
        upload_all: bool = False,
        archive_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full pipeline:
        1. Categorize raw files.
        2. Compress into a .zip archive.
        3. Upload the archive (with failover).
        4. Return summary telemetry.
        """
        logger.info("Starting DictionaryDriveArchiverAgent run.")

        # Step 1: categorize
        categories = self._categorize_raw_files()
        if not categories:
            logger.error("No raw files found to archive.")
            return {"status": "failed", "error": "No raw files found."}

        # Step 2: create archive
        try:
            archive_path = self._create_archive(categories)
        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            return {"status": "failed", "error": f"Compression error: {str(e)}"}

        # Step 3: upload (single archive)
        upload_result = self._upload_single_file(archive_path)

        # Build summary
        summary = {
            "status": upload_result.get("status", "failed"),
            "archive_path": archive_path,
            "archive_size": os.path.getsize(archive_path),
            "categories": {lang: len(files) for lang, files in categories.items()},
            "upload": upload_result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"Run completed. Status: {summary['status']}")
        return summary


# ================================================================
# CLI Entry Point
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="CAIS Dual-Account Google Drive Archiver with Compression and Failover"
    )
    # Primary account (required)
    parser.add_argument("--primary-client-id", required=True, help="Primary OAuth2 client ID")
    parser.add_argument("--primary-client-secret", required=True, help="Primary OAuth2 client secret")
    parser.add_argument("--primary-refresh-token", required=True, help="Primary OAuth2 refresh token")
    parser.add_argument("--primary-folder-id", help="Primary Drive folder ID (optional)")

    # Backup account (optional)
    parser.add_argument("--backup-client-id", help="Backup OAuth2 client ID (optional)")
    parser.add_argument("--backup-client-secret", help="Backup OAuth2 client secret (optional)")
    parser.add_argument("--backup-refresh-token", help="Backup OAuth2 refresh token (optional)")
    parser.add_argument("--backup-folder-id", help="Backup Drive folder ID (optional)")

    # Directories
    parser.add_argument(
        "--raw-dir",
        default=DEFAULT_RAW_DIR,
        help=f"Directory containing raw dictionary files (default: {DEFAULT_RAW_DIR})",
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help=f"Directory to store the generated .zip archive (default: {DEFAULT_ARCHIVE_DIR})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate backup credentials
    backup_provided = any([args.backup_client_id, args.backup_client_secret, args.backup_refresh_token])
    if backup_provided:
        if not (args.backup_client_id and args.backup_client_secret and args.backup_refresh_token):
            logger.error("If providing backup credentials, all three (client-id, client-secret, refresh-token) are required.")
            raise SystemExit(1)

    agent = DictionaryDriveArchiverAgent(
        primary_client_id=args.primary_client_id,
        primary_client_secret=args.primary_client_secret,
        primary_refresh_token=args.primary_refresh_token,
        primary_folder_id=args.primary_folder_id,
        backup_client_id=args.backup_client_id,
        backup_client_secret=args.backup_client_secret,
        backup_refresh_token=args.backup_refresh_token,
        backup_folder_id=args.backup_folder_id,
        raw_dir=args.raw_dir,
        archive_dir=args.archive_dir,
    )

    try:
        summary = agent.run()
        print(json.dumps(summary, indent=2))
        if summary.get("status") == "failed":
            raise SystemExit(1)
        else:
            raise SystemExit(0)
    except Exception as e:
        logger.error(f"Archiving failed: {e}", exc_info=True)
        print(json.dumps({"status": "failed", "error": str(e)}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
