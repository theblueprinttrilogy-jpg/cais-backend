"""
Unit tests for the DriveSyncService.

Uses pytest with mocks to verify Google Drive API interactions,
sync logic, error handling, and credential fallbacks.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.services.drive_sync_service import DriveSyncService, DriveFile


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def mock_oauth_settings():
    """Temporarily add OAuth2 settings attributes to settings."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "test-client-secret"), \
         patch.object(settings, "GOOGLE_REFRESH_TOKEN", "test-refresh-token"), \
         patch.object(settings, "GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"), \
         patch.object(settings, "GCP_CREDENTIALS_JSON", None):
        yield


@pytest.fixture
def mock_service_account_settings():
    """Set GCP_CREDENTIALS_JSON to a dummy service account JSON."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", None), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", None), \
         patch.object(settings, "GOOGLE_REFRESH_TOKEN", None), \
         patch.object(settings, "GCP_CREDENTIALS_JSON", '{"type": "service_account"}'):
        yield


@pytest.fixture
def mock_adc_settings():
    """Remove all credentials so ADC fallback is used."""
    with patch.object(settings, "GOOGLE_CLIENT_ID", None), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", None), \
         patch.object(settings, "GOOGLE_REFRESH_TOKEN", None), \
         patch.object(settings, "GCP_CREDENTIALS_JSON", None):
        yield


@pytest.fixture
def mock_drive_service():
    """
    Create a mock Drive service with common file listing responses.
    """
    with patch("app.services.drive_sync_service.build") as mock_build:
        # Create a mock service instance
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_list = MagicMock()
        mock_execute = MagicMock()

        # Default file list response (two PDF files)
        default_response = {
            "files": [
                {
                    "id": "file1",
                    "name": "doc1.pdf",
                    "mimeType": "application/pdf",
                    "createdTime": "2024-01-01T10:00:00Z",
                    "modifiedTime": "2024-01-02T10:00:00Z",
                    "parents": ["folder1"],
                },
                {
                    "id": "file2",
                    "name": "doc2.pdf",
                    "mimeType": "application/pdf",
                    "createdTime": "2024-01-01T11:00:00Z",
                    "modifiedTime": "2024-01-03T10:00:00Z",
                    "parents": ["folder1"],
                },
            ]
        }
        mock_execute.return_value = default_response
        mock_list.execute = mock_execute
        mock_files.list.return_value = mock_list
        mock_service.files.return_value = mock_files

        # Mock file media download
        mock_media = MagicMock()
        mock_get_media = MagicMock()
        mock_get_media.return_value = mock_media
        mock_service.files().get_media = mock_get_media

        mock_build.return_value = mock_service
        yield mock_service


@pytest.fixture
def drive_service(mock_drive_service, mock_oauth_settings):
    """
    Instantiate DriveSyncService with mocked build and OAuth credentials.
    """
    # The service will call _authenticate, which uses build; we've patched it.
    service = DriveSyncService()
    # Replace the service attribute with our mock for direct control
    service.service = mock_drive_service
    return service


# ----------------------------------------------------------------------
# Tests for initialization & authentication
# ----------------------------------------------------------------------

def test_init_oauth_credentials(mock_oauth_settings):
    """Test that OAuth2 web credentials are used when available."""
    with patch("app.services.drive_sync_service.Credentials") as mock_creds_class, \
         patch("app.services.drive_sync_service.Request") as mock_request, \
         patch("app.services.drive_sync_service.build") as mock_build:

        mock_creds = MagicMock()
        mock_creds_class.return_value = mock_creds
        mock_build.return_value = MagicMock()

        service = DriveSyncService()

        mock_creds_class.assert_called_once_with(
            token=None,
            refresh_token="test-refresh-token",
            client_id="test-client-id",
            client_secret="test-client-secret",
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        mock_creds.refresh.assert_called_once()
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)


def test_init_service_account_fallback(mock_service_account_settings):
    """Test fallback to service account JSON when OAuth credentials are missing."""
    with patch("app.services.drive_sync_service.os.path.exists", return_value=False), \
         patch("app.services.drive_sync_service.json.loads", return_value={"type": "service_account"}), \
         patch("app.services.drive_sync_service.service_account.Credentials.from_service_account_info") as mock_from_info, \
         patch("app.services.drive_sync_service.build") as mock_build:

        mock_from_info.return_value = MagicMock()
        service = DriveSyncService()
        mock_from_info.assert_called_once()
        mock_build.assert_called_once()


def test_init_adc_fallback(mock_adc_settings):
    """Test fallback to Application Default Credentials when nothing else works."""
    with patch("app.services.drive_sync_service.default") as mock_default, \
         patch("app.services.drive_sync_service.build") as mock_build:

        mock_creds = MagicMock()
        mock_default.return_value = (mock_creds, "project")
        service = DriveSyncService()
        mock_default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/drive.readonly"])
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)


def test_init_no_credentials_raises(mock_adc_settings):
    """Test that missing all credentials raises RuntimeError."""
    with patch("app.services.drive_sync_service.default", side_effect=DefaultCredentialsError("No creds")), \
         patch("app.services.drive_sync_service.build"):

        with pytest.raises(RuntimeError, match="No valid Google credentials"):
            DriveSyncService()


# ----------------------------------------------------------------------
# Tests for list_files
# ----------------------------------------------------------------------

def test_list_files_success(drive_service):
    """Test listing files with default query."""
    folder_id = "folder123"
    result = drive_service.list_files(folder_id)
    drive_service.service.files().list.assert_called_once_with(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, parents)",
        pageSize=100,
        pageToken=None,
    )
    assert len(result) == 2
    assert result[0]["id"] == "file1"


def test_list_files_with_mime_filter(drive_service):
    """Test listing files with mime type filter."""
    folder_id = "folder123"
    result = drive_service.list_files(folder_id, mime_type="application/pdf")
    drive_service.service.files().list.assert_called_once_with(
        q=f"'{folder_id}' in parents and trashed = false and mimeType = 'application/pdf'",
        fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, parents)",
        pageSize=100,
        pageToken=None,
    )


def test_list_files_pagination(drive_service):
    """Test pagination: two pages of results."""
    # Mock two pages
    mock_list = drive_service.service.files().list
    first_response = {"files": [{"id": "file1"}], "nextPageToken": "token2"}
    second_response = {"files": [{"id": "file2"}], "nextPageToken": None}
    mock_list.return_value.execute.side_effect = [first_response, second_response]

    result = drive_service.list_files("folder123")
    assert len(result) == 2
    assert mock_list.call_count == 2
    # Check that second call has pageToken
    mock_list.assert_any_call(
        q="'folder123' in parents and trashed = false",
        fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, parents)",
        pageSize=100,
        pageToken=None,
    )
    mock_list.assert_any_call(
        q="'folder123' in parents and trashed = false",
        fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, parents)",
        pageSize=100,
        pageToken="token2",
    )


def test_list_files_http_error(drive_service):
    """Test that HttpError is propagated."""
    drive_service.service.files().list.return_value.execute.side_effect = HttpError(resp=MagicMock(status=404), content=b'Not Found')
    with pytest.raises(HttpError):
        drive_service.list_files("folder123")


# ----------------------------------------------------------------------
# Tests for download_file
# ----------------------------------------------------------------------

def test_download_file_success(drive_service):
    """Test downloading a file returns bytes."""
    # Mock the media downloader
    mock_media = MagicMock()
    drive_service.service.files().get_media.return_value = mock_media

    # Mock MediaIoBaseDownload behavior
    with patch("app.services.drive_sync_service.MediaIoBaseDownload") as mock_downloader_class:
        mock_downloader = MagicMock()
        mock_downloader.next_chunk.side_effect = [
            (MagicMock(progress=lambda: 0.5), False),
            (MagicMock(progress=lambda: 1.0), True),
        ]
        mock_downloader_class.return_value = mock_downloader

        result = drive_service.download_file("file123")
        drive_service.service.files().get_media.assert_called_once_with(fileId="file123")
        assert isinstance(result, bytes)


def test_download_file_http_error(drive_service):
    """Test download failure due to HttpError."""
    drive_service.service.files().get_media.side_effect = HttpError(resp=MagicMock(status=404), content=b'Not Found')
    with pytest.raises(HttpError):
        drive_service.download_file("file123")


# ----------------------------------------------------------------------
# Tests for sync_folder
# ----------------------------------------------------------------------

def test_sync_folder_new_files(drive_service):
    """Test sync_folder downloads new/modified files."""
    # Mock list_files to return two files
    drive_service.list_files = AsyncMock(return_value=[
        {"id": "file1", "name": "doc1.pdf", "mimeType": "application/pdf",
         "modifiedTime": "2024-01-02T10:00:00Z", "createdTime": "2024-01-01T10:00:00Z",
         "parents": ["folder1"]},
        {"id": "file2", "name": "doc2.pdf", "mimeType": "application/pdf",
         "modifiedTime": "2024-01-03T10:00:00Z", "createdTime": "2024-01-01T11:00:00Z",
         "parents": ["folder1"]},
    ])

    # Mock is_file_modified to return True for both (sync state empty)
    drive_service.is_file_modified = AsyncMock(return_value=True)

    # Mock download_file to return bytes
    drive_service.download_file = AsyncMock(return_value=b"PDF content mock")
    drive_service.update_sync_state = AsyncMock()

    result = drive_service.sync_folder("folder1", tags=["test"])
    assert len(result) == 2
    assert isinstance(result[0], DriveFile)
    assert result[0].content == b"PDF content mock"
    assert result[0].tags == ["test"]
    assert drive_service.download_file.call_count == 2
    assert drive_service.update_sync_state.call_count == 2


def test_sync_folder_skip_unmodified(drive_service):
    """Test sync_folder skips files that are not modified."""
    modified_time = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    drive_service.list_files = AsyncMock(return_value=[
        {"id": "file1", "name": "doc1.pdf", "mimeType": "application/pdf",
         "modifiedTime": modified_time.isoformat(), "createdTime": "2024-01-01T10:00:00Z",
         "parents": ["folder1"]},
    ])
    drive_service.is_file_modified = AsyncMock(return_value=False)
    drive_service.download_file = AsyncMock()

    result = drive_service.sync_folder("folder1", tags=["test"])
    assert len(result) == 0
    drive_service.download_file.assert_not_called()


def test_sync_folder_download_failure(drive_service):
    """Test sync_folder continues if one file download fails."""
    drive_service.list_files = AsyncMock(return_value=[
        {"id": "file1", "name": "doc1.pdf", "mimeType": "application/pdf",
         "modifiedTime": "2024-01-02T10:00:00Z", "createdTime": "2024-01-01T10:00:00Z",
         "parents": ["folder1"]},
        {"id": "file2", "name": "doc2.pdf", "mimeType": "application/pdf",
         "modifiedTime": "2024-01-03T10:00:00Z", "createdTime": "2024-01-01T11:00:00Z",
         "parents": ["folder1"]},
    ])
    drive_service.is_file_modified = AsyncMock(return_value=True)
    drive_service.download_file = AsyncMock(side_effect=[b"content1", Exception("Download failed")])
    drive_service.update_sync_state = AsyncMock()

    result = drive_service.sync_folder("folder1", tags=["test"])
    assert len(result) == 1
    assert result[0].file_id == "file1"
    assert drive_service.update_sync_state.call_count == 1


# ----------------------------------------------------------------------
# Tests for sync_jurisdiction_hierarchy
# ----------------------------------------------------------------------

def test_sync_jurisdiction_hierarchy(drive_service):
    """Test synchronising multiple subfolders based on hierarchy mapping."""
    # Mock list_files for root folders and subfolders
    drive_service.list_files = AsyncMock()
    # First call: list root subfolders
    drive_service.list_files.side_effect = [
        # For root: return two folder items
        [
            {"id": "folder_fed", "name": "Federal", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "folder_state", "name": "State", "mimeType": "application/vnd.google-apps.folder"},
        ],
        # For Federal folder: return one file (but sync_folder will be called separately)
        [],
        # For State folder: list subfolders
        [
            {"id": "folder_ca", "name": "California", "mimeType": "application/vnd.google-apps.folder"},
        ],
        # For California folder: return files
        [],
    ]

    # Mock sync_folder to return DriveFile objects
    drive_service.sync_folder = AsyncMock(side_effect=[
        [DriveFile(file_id="file_fed1", name="fed_code.pdf", mime_type="application/pdf",
                   modified_time=datetime(2024,1,1,10,0,0,tzinfo=timezone.utc),
                   content=b"fed", tags=["federal"])],
        [DriveFile(file_id="file_ca1", name="ca_code.pdf", mime_type="application/pdf",
                   modified_time=datetime(2024,1,2,10,0,0,tzinfo=timezone.utc),
                   content=b"ca", tags=["state", "CA"])],
    ])

    hierarchy = {
        "Federal": ["federal"],
        "State/California": ["state", "CA"],
    }
    result = drive_service.sync_jurisdiction_hierarchy("root_id", hierarchy)
    assert len(result) == 2
    assert result[0].file_id == "file_fed1"
    assert result[1].file_id == "file_ca1"
    # Check that sync_folder was called with correct folder IDs and tags
    drive_service.sync_folder.assert_any_call("folder_fed", ["federal"], "application/pdf")
    drive_service.sync_folder.assert_any_call("folder_ca", ["state", "CA"], "application/pdf")


def test_sync_jurisdiction_hierarchy_folder_not_found(drive_service):
    """Test that missing folders are skipped gracefully."""
    drive_service.list_files = AsyncMock(return_value=[])  # no subfolders
    drive_service.sync_folder = AsyncMock()
    hierarchy = {"Federal": ["federal"]}
    result = drive_service.sync_jurisdiction_hierarchy("root_id", hierarchy)
    assert len(result) == 0
    drive_service.sync_folder.assert_not_called()


# ----------------------------------------------------------------------
# Tests for sync state
# ----------------------------------------------------------------------

def test_sync_state_methods(drive_service):
    """Test get_sync_state, load_sync_state, reset_sync_state."""
    # Initially empty
    assert drive_service.get_sync_state() == {}

    # Load state
    state = {"file1": "2024-01-01T10:00:00+00:00"}
    drive_service.load_sync_state(state)
    assert drive_service.get_sync_state() == state

    # Reset
    drive_service.reset_sync_state()
    assert drive_service.get_sync_state() == {}


def test_is_file_modified(drive_service):
    """Test file modification detection."""
    # No sync state -> True
    drive_service._sync_state = {}
    dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert drive_service.is_file_modified("file1", dt) is True

    # Sync state exists with older timestamp -> True
    drive_service._sync_state = {"file1": "2023-12-31T10:00:00+00:00"}
    assert drive_service.is_file_modified("file1", dt) is True

    # Sync state exists with same timestamp -> False
    drive_service._sync_state = {"file1": "2024-01-01T10:00:00+00:00"}
    assert drive_service.is_file_modified("file1", dt) is False

    # Sync state exists with newer timestamp -> False
    drive_service._sync_state = {"file1": "2024-01-02T10:00:00+00:00"}
    assert drive_service.is_file_modified("file1", dt) is False


def test_update_sync_state(drive_service):
    """Test updating sync state with datetime."""
    dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    drive_service.update_sync_state("file1", dt)
    assert drive_service._sync_state["file1"] == "2024-01-01T10:00:00+00:00"


# ----------------------------------------------------------------------
# Tests for get_file_metadata
# ----------------------------------------------------------------------

def test_get_file_metadata_success(drive_service):
    """Test retrieving metadata for a single file."""
    mock_get = MagicMock()
    mock_get.execute.return_value = {"id": "file1", "name": "doc.pdf"}
    drive_service.service.files().get.return_value = mock_get

    result = drive_service.get_file_metadata("file1")
    assert result["id"] == "file1"
    drive_service.service.files().get.assert_called_once_with(fileId="file1", fields="id, name, mimeType, createdTime, modifiedTime, parents")


def test_get_file_metadata_http_error(drive_service):
    """Test get_file_metadata propagates HttpError."""
    drive_service.service.files().get.return_value.execute.side_effect = HttpError(resp=MagicMock(status=404), content=b'Not Found')
    with pytest.raises(HttpError):
        drive_service.get_file_metadata("file1")
