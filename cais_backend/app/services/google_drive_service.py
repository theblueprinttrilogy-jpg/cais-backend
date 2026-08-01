"""
Google Drive Service – Real uploads using service account credentials.

Handles both str and Path for file paths, and provides folder management.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """
    Real Google Drive service using a service account.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, credentials_file: Union[str, Path], folder_id: Optional[str] = None):
        """
        Args:
            credentials_file: Path to service account JSON file (str or Path).
            folder_id: Optional root folder ID (defaults to environment variable).
        """
        self.credentials_file = Path(credentials_file)
        if not self.credentials_file.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

        self.folder_id = folder_id or os.environ.get("DRIVE_FOLDER_ID", "16ywo8njoZ4l7GYKBF1z9CPYQukrmqGVr")
        self.service = self._build_service()

    def _build_service(self):
        creds = service_account.Credentials.from_service_account_file(
            str(self.credentials_file),
            scopes=self.SCOPES
        )
        return build('drive', 'v3', credentials=creds)

    def upload_file(
        self,
        file_path: Union[str, Path],
        folder_id: Optional[str] = None,
        description: str = ""
    ) -> str:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to file (str or Path).
            folder_id: Destination folder ID (defaults to root).
            description: Optional description.

        Returns:
            file_id: ID of uploaded file.
        """
        # Convert to Path and resolve
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        folder = folder_id or self.folder_id
        media = MediaFileUpload(
            str(file_path),
            mimetype='application/pdf',
            resumable=True
        )

        try:
            file = self.service.files().create(
                body={
                    'name': file_path.name,
                    'parents': [folder],
                    'description': description,
                },
                media_body=media,
                fields='id'
            ).execute()
            file_id = file.get('id')
            logger.info(f"Uploaded {file_path.name} to Drive with ID: {file_id}")
            return file_id
        except HttpError as e:
            logger.error(f"Drive upload failed: {e}")
            raise

    def list_files(self, folder_id: Optional[str] = None, mime_type: Optional[str] = None):
        """
        List files in a folder (optional filter by mime_type).
        """
        folder = folder_id or self.folder_id
        query = f"'{folder}' in parents"
        if mime_type:
            query += f" and mimeType='{mime_type}'"

        results = self.service.files().list(
            q=query,
            fields="files(id, name, mimeType, createdTime)",
            pageSize=1000
        ).execute()
        return results.get('files', [])

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Get or create a folder by name under a parent.
        """
        parent = parent_id or self.folder_id
        # Search existing
        query = f"name='{name}' and '{parent}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = self.service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']

        # Create
        body = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent]
        }
        folder = self.service.files().create(body=body, fields='id').execute()
        return folder.get('id')
