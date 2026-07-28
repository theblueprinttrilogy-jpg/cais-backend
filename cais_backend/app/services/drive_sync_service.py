"""
Mock Google Drive Service using local file system storage.

This service simulates the Google Drive API v3 for CAIS backend, allowing
local execution without external credentials. All files and folders are
stored under "storage/drive_mock/" with a hierarchical structure mirroring
the Drive folder tree.

Implements the full interface expected by CAIS agents (list_files, download,
upload, folder creation, sync operations) using asynchronous file I/O.
"""

import asyncio
import io
import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Use aiofiles if available for async file operations, otherwise fallback to asyncio.to_thread
try:
    import aiofiles
except ImportError:
    aiofiles = None

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DriveFile:
    """Metadata and content of a downloaded Drive file."""
    file_id: str
    name: str
    mime_type: str
    modified_time: datetime
    created_time: Optional[datetime] = None
    parents: List[str] = None  # folder IDs
    content: Optional[bytes] = None  # binary content
    tags: List[str] = None  # jurisdictional tags


class DriveSyncService:
    """
    Mock Google Drive service using local disk storage.

    All data is stored under the configured base directory (default: "storage/drive_mock/").
    Folder and file metadata are maintained in memory for fast lookups,
    but folder structures are physically created on disk.

    This mock is fully asynchronous and can be used as a drop-in replacement
    for the real Drive service during development and testing.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialise the mock Drive service.

        Args:
            base_path: Root directory for mock storage. Defaults to "storage/drive_mock/".
        """
        self.base_path = Path(base_path or "storage/drive_mock")
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Root folder ID (simulates Google Drive root)
        self.root_id = "root"
        self.root_path = self.base_path / self.root_id
        self.root_path.mkdir(exist_ok=True)

        # In-memory metadata
        self._folder_paths: Dict[str, Path] = {
            self.root_id: self.root_path  # ID -> absolute Path
        }
        self._folder_id_by_path: Dict[str, str] = {
            str(self.root_path): self.root_id
        }

        self._files_metadata: Dict[str, dict] = {}  # file_id -> metadata dict

        # Sync state (mimics DriveSyncService)
        self._sync_state: Dict[str, str] = {}  # file_id -> last_modified iso string
        self._lock = asyncio.Lock()

        # Ensure base directory exists
        logger.info("Mock Drive Service initialised at %s", self.base_path)

    # ---------- Helper methods ----------

    def _generate_id(self) -> str:
        """Generate a unique ID for a file or folder."""
        return uuid.uuid4().hex

    def _get_file_path(self, file_id: str) -> Optional[Path]:
        """Return the absolute path of a file given its ID."""
        meta = self._files_metadata.get(file_id)
        if not meta:
            return None
        return Path(meta["local_path"])

    def _get_folder_path(self, folder_id: str) -> Optional[Path]:
        """Return the absolute path of a folder given its ID."""
        return self._folder_paths.get(folder_id)

    def _get_folder_id_by_path(self, path: Path) -> Optional[str]:
        """Return the folder ID for a given absolute path."""
        return self._folder_id_by_path.get(str(path))

    def _ensure_path(self, path: Path) -> None:
        """Ensure a directory exists."""
        path.mkdir(parents=True, exist_ok=True)

    async def _async_write_file(self, path: Path, data: bytes) -> None:
        """Write bytes to a file asynchronously."""
        if aiofiles:
            async with aiofiles.open(path, "wb") as f:
                await f.write(data)
        else:
            await asyncio.to_thread(path.write_bytes, data)

    async def _async_read_file(self, path: Path) -> bytes:
        """Read bytes from a file asynchronously."""
        if aiofiles:
            async with aiofiles.open(path, "rb") as f:
                return await f.read()
        else:
            return await asyncio.to_thread(path.read_bytes)

    # ---------- Core public methods ----------

    async def list_files(
        self,
        folder_id: str,
        mime_type: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List files in a given folder, optionally filtered by MIME type.

        Args:
            folder_id: Folder ID (e.g., "root" or a subfolder ID).
            mime_type: Optional MIME type filter.
            page_size: Ignored in mock (returns all).

        Returns:
            List of file metadata dictionaries.
        """
        folder_path = self._get_folder_path(folder_id)
        if not folder_path:
            logger.error("Folder %s not found", folder_id)
            return []

        # Iterate over all files and filter by parent
        result = []
        for file_id, meta in self._files_metadata.items():
            if folder_id in meta.get("parents", []):
                if mime_type and meta.get("mimeType") != mime_type:
                    continue
                # Build a dict matching Drive API response
                result.append({
                    "id": file_id,
                    "name": meta["name"],
                    "mimeType": meta["mimeType"],
                    "createdTime": meta["createdTime"].isoformat(),
                    "modifiedTime": meta["modifiedTime"].isoformat(),
                    "parents": meta["parents"],
                })
        return result

    async def download_file(self, file_id: str) -> bytes:
        """
        Download the binary content of a file.

        Args:
            file_id: File ID.

        Returns:
            Bytes of the file content.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = self._get_file_path(file_id)
        if not path or not path.exists():
            raise FileNotFoundError(f"File {file_id} not found")
        return await self._async_read_file(path)

    async def upload_file(
        self,
        file_path: str,
        parent_folder_id: str,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a local file into the mock storage.

        The file is copied into the target folder with a new unique name.

        Args:
            file_path: Source local file path.
            parent_folder_id: ID of the destination folder.
            file_name: Optional new name for the file.
            mime_type: Optional MIME type (defaults to application/octet-stream).

        Returns:
            Metadata dictionary of the uploaded file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        parent_path = self._get_folder_path(parent_folder_id)
        if not parent_path:
            raise ValueError(f"Parent folder {parent_folder_id} does not exist")

        file_name = file_name or os.path.basename(file_path)
        mime_type = mime_type or "application/octet-stream"

        # Generate a unique ID for the file
        file_id = self._generate_id()
        # Store file with ID as name (preserve extension if any)
        ext = os.path.splitext(file_name)[1]
        dest_path = parent_path / f"{file_id}{ext}"

        # Copy the file
        await asyncio.to_thread(shutil.copy2, file_path, dest_path)

        # Build metadata
        now = datetime.now(timezone.utc)
        metadata = {
            "id": file_id,
            "name": file_name,
            "mimeType": mime_type,
            "createdTime": now,
            "modifiedTime": now,
            "parents": [parent_folder_id],
            "local_path": str(dest_path),
        }
        self._files_metadata[file_id] = metadata

        # Return a dictionary compatible with Drive API
        return {
            "id": file_id,
            "name": file_name,
            "mimeType": mime_type,
            "createdTime": now.isoformat(),
            "modifiedTime": now.isoformat(),
            "parents": [parent_folder_id],
        }

    async def create_folder(self, folder_name: str, parent_folder_id: str) -> Dict[str, Any]:
        """
        Create a new folder in the mock storage.

        Args:
            folder_name: Name of the folder.
            parent_folder_id: ID of the parent folder.

        Returns:
            Metadata dictionary of the created folder.
        """
        parent_path = self._get_folder_path(parent_folder_id)
        if not parent_path:
            raise ValueError(f"Parent folder {parent_folder_id} does not exist")

        folder_id = self._generate_id()
        folder_path = parent_path / folder_name

        if folder_path.exists():
            raise FileExistsError(f"Folder {folder_name} already exists in this location")

        folder_path.mkdir(parents=False, exist_ok=True)

        self._folder_paths[folder_id] = folder_path
        self._folder_id_by_path[str(folder_path)] = folder_id

        now = datetime.now(timezone.utc)
        metadata = {
            "id": folder_id,
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "createdTime": now,
            "modifiedTime": now,
            "parents": [parent_folder_id],
            "local_path": str(folder_path),
        }
        # Also store as a file-like entry? Not needed, but we keep folder metadata separate.

        return {
            "id": folder_id,
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "createdTime": now.isoformat(),
            "modifiedTime": now.isoformat(),
            "parents": [parent_folder_id],
        }

    async def get_or_create_folder(self, folder_name: str, parent_folder_id: str) -> str:
        """
        Get the ID of a folder by name under a parent, or create it if missing.

        Args:
            folder_name: Name of the folder.
            parent_folder_id: ID of the parent folder.

        Returns:
            Folder ID as string.
        """
        parent_path = self._get_folder_path(parent_folder_id)
        if not parent_path:
            raise ValueError(f"Parent folder {parent_folder_id} does not exist")

        folder_path = parent_path / folder_name
        if folder_path.exists() and folder_path.is_dir():
            # Look up its ID
            folder_id = self._folder_id_by_path.get(str(folder_path))
            if folder_id:
                return folder_id
            else:
                # Path exists but no ID registered (should not happen)
                # Regenerate ID and register
                folder_id = self._generate_id()
                self._folder_paths[folder_id] = folder_path
                self._folder_id_by_path[str(folder_path)] = folder_id
                return folder_id
        else:
            # Create it
            folder = await self.create_folder(folder_name, parent_folder_id)
            return folder["id"]

    async def ensure_folder_path(self, path_parts: List[str]) -> Optional[str]:
        """
        Ensure a folder hierarchy exists under the configured root folder.

        Args:
            path_parts: List of folder names (e.g., ["State", "CA"]).

        Returns:
            The ID of the final folder, or None if the root is not accessible.
        """
        if not path_parts:
            return self.root_id

        current_parent = self.root_id
        for part in path_parts:
            try:
                current_parent = await self.get_or_create_folder(part, current_parent)
            except Exception as e:
                logger.error("Error ensuring folder %s under %s: %s", part, current_parent, e)
                return None
        return current_parent

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Retrieve full metadata for a single file."""
        meta = self._files_metadata.get(file_id)
        if not meta:
            raise FileNotFoundError(f"File {file_id} not found")
        return {
            "id": meta["id"],
            "name": meta["name"],
            "mimeType": meta["mimeType"],
            "createdTime": meta["createdTime"].isoformat(),
            "modifiedTime": meta["modifiedTime"].isoformat(),
            "parents": meta["parents"],
        }

    async def is_file_modified(self, file_id: str, modified_time: datetime) -> bool:
        """Check if the file has been modified since the last sync (mock)."""
        async with self._lock:
            last_sync = self._sync_state.get(file_id)
            if last_sync is None:
                return True
            last_sync_dt = datetime.fromisoformat(last_sync)
            return modified_time > last_sync_dt

    async def update_sync_state(self, file_id: str, modified_time: datetime) -> None:
        """Store the current modified time for a file."""
        async with self._lock:
            self._sync_state[file_id] = modified_time.isoformat()

    async def sync_folder(
        self,
        folder_id: str,
        jurisdiction_tags: List[str],
        mime_type: Optional[str] = "application/pdf",
    ) -> List[DriveFile]:
        """
        Sync a specific folder: list files, download new/modified ones,
        and return DriveFile objects with content.

        In the mock, this simulates downloading by reading the files from disk
        and returning their content.
        """
        files_meta = await self.list_files(folder_id, mime_type)
        downloaded = []
        for meta in files_meta:
            file_id = meta["id"]
            modified_time = datetime.fromisoformat(meta["modifiedTime"].replace("Z", "+00:00"))

            if await self.is_file_modified(file_id, modified_time):
                logger.info("Downloading file: %s (%s)", meta["name"], file_id)
                try:
                    content = await self.download_file(file_id)
                    drive_file = DriveFile(
                        file_id=file_id,
                        name=meta["name"],
                        mime_type=meta["mimeType"],
                        modified_time=modified_time,
                        created_time=datetime.fromisoformat(meta["createdTime"].replace("Z", "+00:00")),
                        parents=meta.get("parents", []),
                        content=content,
                        tags=jurisdiction_tags.copy(),
                    )
                    downloaded.append(drive_file)
                    await self.update_sync_state(file_id, modified_time)
                except Exception as e:
                    logger.error("Failed to download file %s: %s", file_id, e)
            else:
                logger.debug("Skipping file (no change): %s", meta["name"])
        return downloaded

    async def sync_jurisdiction_hierarchy(
        self,
        root_folder_id: str,
        hierarchy_mapping: Dict[str, List[str]],
        mime_type: Optional[str] = "application/pdf",
    ) -> List[DriveFile]:
        """
        Recursively sync folders based on a hierarchy mapping.

        In the mock, this traverses the local folder structure according to the
        mapping, and syncs each found folder.
        """
        all_files = []
        # For each path, ensure it exists and get its ID
        for folder_path, tags in hierarchy_mapping.items():
            parts = folder_path.split("/")
            folder_id = await self.ensure_folder_path(parts)
            if folder_id:
                logger.info("Syncing folder: %s with tags %s", folder_path, tags)
                files = await self.sync_folder(folder_id, tags, mime_type)
                all_files.extend(files)
        return all_files

    def get_sync_state(self) -> Dict[str, str]:
        """Return the current sync state (file_id -> last_modified)."""
        return self._sync_state.copy()

    async def load_sync_state(self, state: Dict[str, str]) -> None:
        """Restore sync state from a saved dictionary."""
        async with self._lock:
            self._sync_state.update(state)

    async def reset_sync_state(self) -> None:
        """Clear all sync state (force re-download on next sync)."""
        async with self._lock:
            self._sync_state.clear()
