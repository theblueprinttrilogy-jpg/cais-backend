"""
Google Drive Downloader for CAIS
Downloads files from Google Drive by category.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from modules.google_drive.connector import GoogleDriveConnector


class GoogleDriveDownloader:
    """Downloads files from Google Drive by category."""

    def __init__(self, credentials_path: Optional[str] = None, output_dir: str = "/downloads"):
        self.connector = GoogleDriveConnector(credentials_path)
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_by_category(self, category_name: str, max_files: Optional[int] = None) -> Dict:
        """Download all files from a category in Google Drive."""
        print(f"\n Searching for folder: {category_name}")

        folder_id = self.connector.find_folder_by_name(category_name)

        if folder_id is None:
            print(f" Folder '{category_name}' not found in Google Drive")
            return {'success': False, 'error': 'Folder not found'}

        print(f" Folder found (ID: {folder_id})")

        files = self.connector.list_files(folder_id=folder_id)

        if not files:
            print(f" No files in folder '{category_name}'")
            return {'success': True, 'downloaded': 0, 'total': 0}

        if max_files:
            files = files[:max_files]

        total_files = len(files)
        downloaded = 0
        failed = 0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_folder = self.output_dir / f"{category_name}_{timestamp}"
        download_folder.mkdir(parents=True, exist_ok=True)

        print(f"\n Downloading {total_files} files...")
        print("-" * 50)

        for idx, file_info in enumerate(files, 1):
            file_id = file_info['id']
            file_name = file_info['name']
            file_size = int(file_info.get('size', 0))
            file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0

            safe_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
            destination = download_folder / safe_name

            print(f"{idx}/{total_files} {file_name} ({file_size_mb} MB)", end=" ")

            success = self.connector.download_file(file_id, str(destination))

            if success:
                downloaded += 1
                print("OK")
            else:
                failed += 1
                print("FAILED")

        print("-" * 50)
        print(f"\n DOWNLOAD SUMMARY:")
        print(f" Downloaded: {downloaded}")
        print(f" Failed: {failed}")
        print(f" Total: {total_files}")
        print(f" Saved in: {download_folder}")

        return {
            'success': True,
            'category': category_name,
            'downloaded': downloaded,
            'failed': failed,
            'total': total_files,
            'folder': str(download_folder)
        }
