import io
import logging
import os
from typing import List, Optional, Dict, Any, Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)


class GoogleDriveUploader:
    """
    Service for interacting with Google Drive API.
    Provides methods for folder/file operations and downloads.
    """

    def __init__(self, credentials_path: Optional[str] = None) -> None:
        """
        Initialize the Google Drive service.

        :param credentials_path: Path to the service account credentials JSON file.
                                 If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "No credentials path provided and GOOGLE_APPLICATION_CREDENTIALS not set."
            )

        self.credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        self.service = build("drive", "v3", credentials=self.credentials)

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a new folder in Google Drive.

        :param folder_name: Name of the folder to create.
        :param parent_folder_id: ID of the parent folder (optional).
        :return: ID of the created folder.
        """
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        try:
            folder = self.service.files().create(
                body=file_metadata,
                fields="id",
            ).execute()
            folder_id = folder.get("id")
            logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
        except HttpError as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise

    def upload_file(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        """
        Upload a local file to Google Drive.

        :param file_path: Path to the local file.
        :param file_name: Name to give the file in Drive (defaults to basename).
        :param parent_folder_id: ID of the parent folder (optional).
        :param mime_type: MIME type of the file (optional, auto-detected).
        :return: ID of the uploaded file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = file_name or os.path.basename(file_path)
        file_metadata = {"name": file_name}
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()
            file_id = file.get("id")
            logger.info(f"Uploaded file '{file_name}' with ID: {file_id}")
            return file_id
        except HttpError as e:
            logger.error(f"Failed to upload file '{file_name}': {e}")
            raise

    def list_files(
        self,
        query: Optional[str] = None,
        page_size: int = 100,
        fields: str = "files(id, name, mimeType, parents, createdTime, modifiedTime, size)",
    ) -> Dict[str, Any]:
        """
        List files in Google Drive matching the query.

        :param query: Search query (e.g., "mimeType='application/pdf'").
        :param page_size: Maximum number of files to return per page.
        :param fields: Fields to include in the response.
        :return: Dictionary containing 'files' key with list of file metadata.
        """
        try:
            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields=f"nextPageToken, {fields}",
                )
                .execute()
            )
            files = results.get("files", [])
            logger.debug(f"Listed {len(files)} files matching query: {query}")
            return results
        except HttpError as e:
            logger.error(f"Failed to list files: {e}")
            raise

    def delete_file(self, file_id: str) -> None:
        """
        Permanently delete a file from Google Drive.

        :param file_id: ID of the file to delete.
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file with ID: {file_id}")
        except HttpError as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            raise

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve metadata for a specific file.

        :param file_id: ID of the file.
        :return: Dictionary containing file metadata.
        """
        try:
            metadata = (
                self.service.files()
                .get(fileId=file_id, fields="id, name, mimeType, parents, createdTime, modifiedTime, size")
                .execute()
            )
            logger.debug(f"Retrieved metadata for file {file_id}")
            return metadata
        except HttpError as e:
            logger.error(f"Failed to get metadata for file {file_id}: {e}")
            raise

    def download_file(self, file_id: str) -> bytes:
        """
        Download the binary content of a file from Google Drive.

        This method uses MediaIoBaseDownload to stream the file content into a
        BytesIO buffer, then returns the raw bytes.

        :param file_id: ID of the file to download.
        :return: Bytes content of the file.
        :raises HttpError: If the download fails.
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")

            file_handle.seek(0)
            content = file_handle.read()
            logger.info(f"Successfully downloaded file ID: {file_id} ({len(content)} bytes)")
            return content

        except HttpError as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during download of {file_id}: {e}")
            raise

    def close(self) -> None:
        """
        Clean up resources (currently a no-op, but provided for compatibility).
        """
        pass
GoogleDriveService = GoogleDriveUploader
