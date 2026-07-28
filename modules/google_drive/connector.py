"""
Google Drive Connector for CAIS
Authenticates with Google Drive using service account.
"""

import os
import json
from pathlib import Path
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleDriveConnector:
    """
    Authenticates with Google Drive using a service account.
    Provides read-only access for document acquisition.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the authenticator.

        Args:
            credentials_path: Path to the service account JSON key file.
        """
        if credentials_path is None:
            credentials_path = os.getenv(
                'GOOGLE_APPLICATION_CREDENTIALS',
                '/home/maxlo/cais_new/docker/credentials/service-account.json'
            )

        self.credentials_path = Path(credentials_path).expanduser()

        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found at {self.credentials_path}"
            )

        self._service = None
        self.user_email = None

    def authenticate(self):
        """Authenticate and build the Drive service object."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.SCOPES
            )

            self.user_email = credentials.service_account_email
            self._service = build('drive', 'v3', credentials=credentials)
            return self._service

        except Exception as e:
            raise RuntimeError(f"Failed to authenticate with Google Drive: {e}")

    def get_service(self):
        """Get the Drive service object, authenticating if necessary."""
        if not self._service:
            self.authenticate()
        return self._service

    def test_connection(self) -> bool:
        """Test the connection to Google Drive."""
        try:
            service = self.get_service()
            service.files().list(pageSize=1).execute()
            return True
        except HttpError as e:
            print(f"Connection test failed: {e}")
            return False

    def list_files(self, folder_id: Optional[str] = None, query: Optional[str] = None):
        """List files in a folder or matching a search query."""
        service = self.get_service()

        q_parts = ["trashed=false"]
        if folder_id and folder_id != 'root':
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"name contains '{query}'")

        q = " and ".join(q_parts)

        try:
            response = service.files().list(
                q=q,
                spaces='drive',
                fields='files(id, name, mimeType, size, modifiedTime, webViewLink, parents)',
                pageSize=100
            ).execute()
            return response.get('files', [])
        except HttpError as e:
            print(f"Error listing files: {e}")
            return []

    def find_folder_by_name(self, name: str) -> Optional[str]:
        """Find a folder by name in Google Drive."""
        service = self.get_service()

        try:
            response = service.files().list(
                q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                pageSize=10,
                fields="files(id, name)"
            ).execute()

            folders = response.get('files', [])
            if folders:
                return folders[0]['id']
            return None

        except HttpError as e:
            print(f"Error finding folder: {e}")
            return None

    def download_file(self, file_id: str, destination_path: str) -> bool:
        """Download a file from Google Drive by ID."""
        service = self.get_service()

        try:
            request = service.files().get_media(fileId=file_id)

            with open(destination_path, 'wb') as f:
                downloader = request.execute()
                f.write(downloader)

            return True

        except HttpError as e:
            print(f"Error downloading file: {e}")
            return False
