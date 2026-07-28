# app/agents/janitor_agent.py - Janitor Agent for CAIS v2.0
# Production-ready agent that scans local directories for files older than 45 days,
# uploads them to Google Drive under JACINTO_CORREA_COMPUTER folder,
# and safely purges local files only after successful remote archiving.

import os
import shutil
import time
import logging
import tarfile
import tempfile
import threading
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configure logger
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_AGE_DAYS = 45
DEFAULT_FALLBACK_DIR = "/tmp/cais_janitor_fallback"
DEFAULT_CREDENTIALS_FILE = "secrets/credentials.json"
DEFAULT_TOKEN_FILE = "secrets/token.json"
DEFAULT_ROOT_FOLDER_NAME = "JACINTO_CORREA_COMPUTER"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE_ACCOUNT_EMAIL = "caiscodecompliance@gmail.com"


class JanitorAgent:
    """
    Janitor Agent responsible for archiving and safely purging aged local files.
    Files older than 45 days are compressed into .tar.gz archives and uploaded
    to Google Drive under the JACINTO_CORREA_COMPUTER folder.
    Local files are only deleted after successful remote upload verification.
    """

    def __init__(
        self,
        credentials_file: str = DEFAULT_CREDENTIALS_FILE,
        token_file: str = DEFAULT_TOKEN_FILE,
        root_folder_name: str = DEFAULT_ROOT_FOLDER_NAME,
        fallback_dir: str = DEFAULT_FALLBACK_DIR,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    ):
        """
        Initialize the JanitorAgent with OAuth 2.0 user authentication.

        Args:
            credentials_file: Path to the OAuth client secrets JSON file.
            token_file: Path to store/load the user token.
            root_folder_name: Name of the root Drive folder for uploads.
            fallback_dir: Local directory for fallback storage when upload fails.
            max_age_days: Number of days after which files are considered aged.
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.root_folder_name = root_folder_name
        self.fallback_dir = fallback_dir
        self.max_age_days = max_age_days

        # Lock for thread-safe operations
        self._lock = threading.Lock()

        # Validate credentials file exists
        if not os.path.isfile(self.credentials_file):
            raise FileNotFoundError(
                f"OAuth client secrets file not found: {self.credentials_file}"
            )

        # Build the Drive service with user authentication
        self.service = self._build_service()

        # Ensure the root folder exists and store its ID
        self.root_folder_id = self._ensure_root_folder()

        # Ensure fallback directory exists
        os.makedirs(self.fallback_dir, exist_ok=True)

        # Track upload verification
        self._uploaded_file_ids: List[str] = []

        logger.info(
            f"JanitorAgent initialized: root_folder='{self.root_folder_name}', "
            f"fallback='{self.fallback_dir}', max_age={self.max_age_days} days"
        )

    def _build_service(self):
        """
        Authenticate using OAuth 2.0 with user credentials via console-based out-of-band flow.
        Uses cached token if available; otherwise runs the console flow.
        Returns a Drive API service object.
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded cached user token.")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}. Will re-authenticate.")

        # If no valid credentials, run the OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully.")
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Re-running flow.")
                    creds = None

            if not creds:
                # Use out-of-band (OOB) flow for console/terminal environments
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                # Set the redirect URI to the OOB value
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

                # Generate the authorization URL with consent prompt
                auth_url, _ = flow.authorization_url(prompt='consent')

                # Print instructions for the user
                print("\n" + "=" * 80)
                print("JANITOR AGENT AUTHENTICATION REQUIRED")
                print("=" * 80)
                print(f"Please open the following URL in your browser:")
                print(f"\n{auth_url}\n")
                print(f"Sign in with the account: {DRIVE_ACCOUNT_EMAIL}")
                print("Grant the requested permissions, and then copy the")
                print("authorization code provided by Google.")
                print("=" * 80)

                code = input("\nEnter the authorization code: ").strip()

                try:
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    logger.info("OAuth flow completed, new credentials obtained.")
                except Exception as e:
                    logger.error(f"Failed to fetch token: {e}")
                    raise

            # Save the credentials for next time
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Saved user token to {self.token_file}")
            except Exception as e:
                logger.warning(f"Could not save token: {e}")

        # Build the Drive service
        return build("drive", "v3", credentials=creds)

    def _ensure_root_folder(self) -> str:
        """
        Search for the root folder by name; if not found, create it.
        Returns the folder ID.
        """
        query = (
            f"name='{self.root_folder_name}' "
            "and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        )
        results = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True
        ).execute()
        folders = results.get("files", [])

        if folders:
            folder_id = folders[0]["id"]
            logger.info(f"Found existing root folder '{self.root_folder_name}' (ID: {folder_id})")
            return folder_id
        else:
            # Create the folder
            file_metadata = {
                "name": self.root_folder_name,
                "mimeType": "application/vnd.google-apps.folder"
            }
            try:
                folder = self.service.files().create(
                    body=file_metadata,
                    fields="id",
                    supportsAllDrives=True
                ).execute()
                folder_id = folder.get("id")
                logger.info(f"Created root folder '{self.root_folder_name}' (ID: {folder_id})")
                return folder_id
            except HttpError as e:
                logger.error(f"Failed to create root folder: {e}")
                raise

    def _find_or_create_subfolder(self, parent_id: str, folder_name: str) -> str:
        """
        Find or create a subfolder under a parent.
        """
        query = (
            f"name='{folder_name}' "
            "and mimeType='application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents "
            "and trashed=false"
        )
        results = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True
        ).execute()
        folders = results.get("files", [])

        if folders:
            return folders[0]["id"]
        else:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id]
            }
            folder = self.service.files().create(
                body=file_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()
            return folder.get("id")

    def _upload_file(self, file_path: str, parent_folder_id: str, file_name: Optional[str] = None) -> str:
        """
        Upload a file to a Drive folder using resumable media upload.
        Returns the uploaded file ID.

        Raises:
            HttpError: If upload fails.
        """
        if file_name is None:
            file_name = os.path.basename(file_path)
        media = MediaFileUpload(
            file_path,
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )
        file_metadata = {
            "name": file_name,
            "parents": [parent_folder_id]
        }
        try:
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            )
            response = request.execute()
            file_id = response.get("id")
            logger.info(f"Uploaded '{file_name}' to Drive (ID: {file_id})")
            return file_id
        except HttpError as e:
            logger.error(f"Upload failed: {e}")
            raise

    def _verify_upload(self, file_id: str) -> bool:
        """
        Verify that a file exists in Drive with the given ID.
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, modifiedTime",
                supportsAllDrives=True
            ).execute()
            if file.get("id"):
                logger.debug(f"Verified file exists in Drive: {file_id} - {file.get('name')}")
                return True
            return False
        except HttpError as e:
            logger.error(f"Verification failed for {file_id}: {e}")
            return False

    def _create_archive(self, files: List[str], archive_name: str) -> str:
        """
        Create a .tar.gz archive containing the given files.
        Returns the path to the created archive.
        """
        temp_dir = tempfile.mkdtemp(prefix="janitor_archive_")
        archive_path = os.path.join(temp_dir, f"{archive_name}.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar:
            for fpath in files:
                arcname = os.path.basename(fpath)
                tar.add(fpath, arcname=arcname)
        logger.debug(f"Created archive: {archive_path} with {len(files)} files")
        return archive_path

    def _save_to_fallback(self, archive_path: str, source_dir: str) -> str:
        """
        Save the archive to the local fallback directory.
        Returns the path where the archive was saved.
        """
        os.makedirs(self.fallback_dir, exist_ok=True)
        safe_dirname = source_dir.replace('/', '_').replace(' ', '_')
        dest_dir = os.path.join(self.fallback_dir, safe_dirname)
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, os.path.basename(archive_path))
        shutil.copy2(archive_path, dest_file)
        logger.info(f"Saved archive to fallback: {dest_file}")
        return dest_file

    def _get_aged_files(self, directory: str) -> List[str]:
        """
        Recursively scan a directory and return list of file paths
        whose last modification time is older than max_age_days.
        """
        aged_files = []
        cutoff = time.time() - (self.max_age_days * 86400)
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime < cutoff:
                        aged_files.append(file_path)
                except OSError as e:
                    logger.warning(f"Could not access {file_path}: {e}")
        return aged_files

    def archive_and_purge_directory(self, directory: str) -> Dict[str, Any]:
        """
        Process a directory: scan for aged files, compress them into a .tar.gz,
        upload to Google Drive, verify the upload, and then safely delete local files.

        Args:
            directory: The local directory to scan.

        Returns:
            A dictionary with status and details.

        Raises:
            Exception: If upload fails and fallback also fails.
        """
        if not os.path.isdir(directory):
            logger.error(f"Directory not found: {directory}")
            return {"status": "FAILED", "reason": "Directory not found", "directory": directory}

        with self._lock:
            logger.info(f"Processing directory: {directory}")
            aged_files = self._get_aged_files(directory)
            if not aged_files:
                logger.info(f"No aged files found in {directory} (>{self.max_age_days} days)")
                return {"status": "NO_FILES", "directory": directory, "count": 0}

            logger.info(f"Found {len(aged_files)} aged files in {directory}")

            # Create archive
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_name = f"archive_{os.path.basename(directory)}_{timestamp}"
            archive_path = self._create_archive(aged_files, safe_name)

            # Determine Drive folder structure: root / directory_name
            subfolder_name = os.path.basename(directory)
            subfolder_id = self._find_or_create_subfolder(self.root_folder_id, subfolder_name)

            # Upload archive to Drive
            try:
                file_id = self._upload_file(archive_path, subfolder_id, f"{safe_name}.tar.gz")
                # Verify the upload
                if not self._verify_upload(file_id):
                    raise RuntimeError(f"Upload verification failed for file ID: {file_id}")
                # Record successful upload
                self._uploaded_file_ids.append(file_id)
                logger.info(f"Successfully uploaded and verified: {file_id}")

                # ---- SAFE PURGE: Only delete after verification ----
                for fpath in aged_files:
                    try:
                        os.remove(fpath)
                        logger.debug(f"Purged local file: {fpath}")
                    except OSError as e:
                        logger.warning(f"Failed to delete {fpath}: {e}")

                # Clean up archive temp
                try:
                    os.remove(archive_path)
                    shutil.rmtree(os.path.dirname(archive_path))
                except Exception as e:
                    logger.warning(f"Failed to clean up archive temp: {e}")

                return {
                    "status": "SUCCESS",
                    "directory": directory,
                    "file_count": len(aged_files),
                    "drive_file_id": file_id,
                    "folder": f"{self.root_folder_name}/{subfolder_name}"
                }

            except Exception as e:
                # Upload or verification failed: fallback to local storage
                logger.error(f"Upload failed: {e}. Falling back to local storage.")
                fallback_path = self._save_to_fallback(archive_path, directory)

                # Clean up archive temp but keep fallback
                try:
                    os.remove(archive_path)
                    shutil.rmtree(os.path.dirname(archive_path))
                except Exception as cleanup_e:
                    logger.warning(f"Cleanup of archive temp failed: {cleanup_e}")

                # DO NOT DELETE aged files; they remain safely on disk
                return {
                    "status": "FALLBACK",
                    "directory": directory,
                    "file_count": len(aged_files),
                    "fallback_path": fallback_path,
                    "error": str(e)
                }

    def run_sweep(self, directories: List[str]) -> Dict[str, Any]:
        """
        Run a full sweep across multiple directories.
        Processes each directory in sequence (thread-safe individually).
        Returns a summary report.

        Args:
            directories: List of directory paths to process.

        Returns:
            Summary dictionary with totals and per-directory results.
        """
        logger.info(f"Starting sweep over {len(directories)} directories.")
        results = []
        total_files_archived = 0
        total_success = 0
        total_fallback = 0
        total_fail = 0

        for directory in directories:
            result = self.archive_and_purge_directory(directory)
            results.append(result)
            if result.get("status") == "SUCCESS":
                total_success += 1
                total_files_archived += result.get("file_count", 0)
            elif result.get("status") == "FALLBACK":
                total_fallback += 1
                total_files_archived += result.get("file_count", 0)
            elif result.get("status") == "FAILED":
                total_fail += 1

        summary = {
            "total_directories": len(directories),
            "successful": total_success,
            "fallback": total_fallback,
            "failed": total_fail,
            "total_files_archived": total_files_archived,
            "details": results,
            "timestamp": datetime.utcnow().isoformat(),
            "uploaded_file_ids": self._uploaded_file_ids,
        }
        logger.info(f"Sweep completed: {summary}")
        return summary

    def get_uploaded_file_ids(self) -> List[str]:
        """Return the list of successfully uploaded file IDs."""
        return self._uploaded_file_ids.copy()

    def reset_tracking(self) -> None:
        """Reset the tracking of uploaded file IDs."""
        self._uploaded_file_ids = []
