import os
import logging
from typing import Optional, List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)


class GoogleDriveUploader:
    """
    Headless Google Drive uploader using service account authentication.
    Designed for automated containerized environments on GCP.
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        default_parent_folder_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the GoogleDriveUploader.

        Args:
            credentials_path: Path to the service account JSON credentials file.
                              If None, defaults to the GCP_CREDENTIALS_JSON environment
                              variable or "app/credentials/service-account.json".
            default_parent_folder_id: Default parent folder ID for uploads.
        """
        self.default_parent_folder_id = default_parent_folder_id
        self.credentials_path = self._resolve_credentials_path(credentials_path)
        self._validate_credentials_file()
        self.service = None
        self._authenticate()

    def _resolve_credentials_path(self, provided_path: Optional[str]) -> str:
        """Resolve the credentials file path from arguments or environment."""
        if provided_path is not None:
            return provided_path
        env_path = os.environ.get("GCP_CREDENTIALS_JSON")
        if env_path is not None:
            return env_path
        return "app/credentials/service-account.json"

    def _validate_credentials_file(self) -> None:
        """Check that the credentials file exists; raise FileNotFoundError if not."""
        if not os.path.isfile(self.credentials_path):
            raise FileNotFoundError(
                f"Service account credentials file not found: {self.credentials_path}"
            )

    def _authenticate(self) -> None:
        """
        Authenticate using the service account credentials and build the Drive service.
        Raises GoogleAuthError on authentication failure.
        """
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build("drive", "v3", credentials=creds)
            logger.info("Successfully authenticated with Google Drive service account.")
        except Exception as e:
            logger.error("Authentication failed: %s", e, exc_info=True)
            raise GoogleAuthError(f"Failed to authenticate: {e}") from e

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create.
            parent_folder_id: Optional parent folder ID. If not provided, uses default.

        Returns:
            The created folder's metadata (including 'id').

        Raises:
            HttpError: If the API call fails.
        """
        parent = parent_folder_id or self.default_parent_folder_id
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent:
            folder_metadata["parents"] = [parent]

        try:
            folder = (
                self.service.files()
                .create(body=folder_metadata, fields="id, name, mimeType, parents")
                .execute()
            )
            logger.info('Created folder "%s" with ID: %s', folder_name, folder.get("id"))
            return folder
        except HttpError as e:
            logger.error("Failed to create folder '%s': %s", folder_name, e, exc_info=True)
            raise

    def upload_file(
        self,
        file_path: str,
        mime_type: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a local file to Google Drive.

        Args:
            file_path: Local path to the file to upload.
            mime_type: MIME type of the file. If None, it will be guessed.
            parent_folder_id: Optional parent folder ID. Uses default if not provided.
            file_name: Optional name for the file in Drive. If None, uses the local filename.

        Returns:
            The uploaded file's metadata (including 'id').

        Raises:
            FileNotFoundError: If the local file does not exist.
            HttpError: If the API call fails.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        parent = parent_folder_id or self.default_parent_folder_id
        name = file_name or os.path.basename(file_path)

        file_metadata = {"name": name}
        if parent:
            file_metadata["parents"] = [parent]

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        try:
            uploaded = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, name, mimeType, parents")
                .execute()
            )
            logger.info('Uploaded "%s" (ID: %s) to Drive.', name, uploaded.get("id"))
            return uploaded
        except HttpError as e:
            logger.error("Failed to upload file '%s': %s", file_path, e, exc_info=True)
            raise

    def list_files(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        fields: str = "files(id, name, mimeType, parents, createdTime, size), nextPageToken",
    ) -> Dict[str, Any]:
        """
        List files in Google Drive with pagination support.

        Args:
            page_size: Number of files per page (max 1000).
            page_token: Token for the next page of results.
            query: Optional query string (e.g., "mimeType='application/vnd.google-apps.folder'").
            fields: Fields to include in the response.

        Returns:
            A dict containing 'files' (list of file metadata) and 'nextPageToken' if any.
        """
        try:
            request = self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields=fields,
                orderBy="name asc",
            )
            response = request.execute()
            logger.debug(
                "Listed %d files, nextPageToken: %s",
                len(response.get("files", [])),
                response.get("nextPageToken"),
            )
            return response
        except HttpError as e:
            logger.error("Failed to list files: %s", e, exc_info=True)
            raise

    def delete_file(self, file_id: str) -> None:
        """
        Permanently delete a file or folder from Google Drive.

        Args:
            file_id: The ID of the file/folder to delete.

        Raises:
            HttpError: If the API call fails.
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info("Deleted file/folder with ID: %s", file_id)
        except HttpError as e:
            logger.error("Failed to delete file ID %s: %s", file_id, e, exc_info=True)
            raise

    def get_file_metadata(self, file_id: str, fields: str = "id, name, mimeType, parents, createdTime, size") -> Dict[str, Any]:
        """
        Retrieve metadata for a specific file or folder.

        Args:
            file_id: The ID of the file/folder.
            fields: Fields to include in the response.

        Returns:
            The file metadata as a dictionary.

        Raises:
            HttpError: If the API call fails.
        """
        try:
            metadata = (
                self.service.files()
                .get(fileId=file_id, fields=fields)
                .execute()
            )
            logger.debug("Retrieved metadata for file ID %s", file_id)
            return metadata
        except HttpError as e:
            logger.error("Failed to get metadata for file ID %s: %s", file_id, e, exc_info=True)
            raise


class GoogleAuthError(Exception):
    """Exception raised for Google Drive authentication errors."""
    pass
GoogleDriveService = GoogleDriveUploader
