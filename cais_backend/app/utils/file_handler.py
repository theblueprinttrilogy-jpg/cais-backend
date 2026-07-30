"""
File Handler - File Management Utilities

This module provides utilities for file operations.
"""

import os
import shutil
import uuid
import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime

from app.core.config import settings


class FileHandler:
    """
    File handler for file operations.
    """

    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.STORAGE_PATH
        self._ensure_directory(self.base_path)

    def _ensure_directory(self, path: str):
        """Ensure a directory exists."""
        Path(path).mkdir(parents=True, exist_ok=True)

    def get_storage_path(self, subdir: str = "") -> str:
        """Get storage path for a subdirectory."""
        path = os.path.join(self.base_path, subdir)
        self._ensure_directory(path)
        return path

    def generate_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        name, ext = os.path.splitext(original_filename)
        return f"{timestamp}_{unique_id}_{name}{ext}"

    def save_file(
        self,
        file_content: bytes,
        filename: str,
        subdir: str = "uploads"
    ) -> str:
        """
        Save a file to storage.
        """
        storage_dir = self.get_storage_path(subdir)
        file_path = os.path.join(storage_dir, filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        return file_path

    def save_file_from_stream(
        self,
        file_stream: BinaryIO,
        filename: str,
        subdir: str = "uploads"
    ) -> str:
        """
        Save a file from a stream.
        """
        content = file_stream.read()
        return self.save_file(content, filename, subdir)

    def read_file(self, file_path: str) -> bytes:
        """
        Read a file from storage.
        """
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def delete_directory(self, dir_path: str) -> bool:
        """
        Delete a directory and its contents.
        """
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                return True
            return False
        except Exception:
            return False

    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        """
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    def get_file_hash(self, file_path: str, algorithm: str = "sha256") -> str:
        """
        Get file hash.
        """
        hasher = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_file_info(self, file_path: str) -> dict:
        """
        Get file information.
        """
        if not os.path.exists(file_path):
            return {}

        stat = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "hash": self.get_file_hash(file_path),
        }

    def validate_file_type(self, filename: str, allowed_extensions: list) -> bool:
        """
        Validate file type by extension.
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in allowed_extensions
