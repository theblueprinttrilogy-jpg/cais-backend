#!/usr/bin/env python3
"""
Janitor Agent - CAIS - FIXED VERSION
Uses service account credentials directly.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import shutil
import time
import logging
import tarfile
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from modules.google_drive.connector import GoogleDriveConnector
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configure logger
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_AGE_DAYS = 45
DEFAULT_ROOT_FOLDER_NAME = "JACINTO_CORREA_COMPUTER"
SCOPES = ["https://www.googleapis.com/auth/drive"]


class JanitorAgent:
    """
    Janitor Agent - Moves old files to Google Drive.
    Uses service account credentials.
    """
    
    def __init__(
        self,
        credentials_file: str = "/home/maxlo/cais_new/docker/credentials/service-account.json",
        root_folder_name: str = DEFAULT_ROOT_FOLDER_NAME,
        fallback_dir: str = "/tmp/cais_janitor_fallback",
        max_age_days: int = 45,
        directories: List[str] = None
    ):
        self.credentials_file = credentials_file
        self.root_folder_name = root_folder_name
        self.fallback_dir = fallback_dir
        self.max_age_days = max_age_days
        self.directories = directories or [
            '/home/maxlo/PROMETHEUS/downloads',
            '/home/maxlo/PROMETHEUS/evidence',
            '/home/maxlo/PROMETHEUS/compressed',
            '/home/maxlo/PROMETHEUS/logs'
        ]
        
        # Build service using connector
        self.connector = GoogleDriveConnector(credentials_file)
        self.service = self.connector.get_service()
        
        # Ensure root folder exists
        self.root_folder_id = self._ensure_root_folder()
        
        # Stats
        self.stats = {
            'total_directories': 0,
            'successful': 0,
            'failed': 0,
            'fallback': 0,
            'total_files_archived': 0,
            'uploaded_file_ids': [],
            'details': []
        }
        
        logger.info(f"✅ JanitorAgent initialized: root_folder='{root_folder_name}'")
    
    def _ensure_root_folder(self) -> str:
        """Ensure root folder exists in Drive."""
        try:
            # Search for existing folder
            results = self.service.files().list(
                q=f"name='{self.root_folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"📁 Root folder found: {self.root_folder_name} (ID: {folder_id})")
                return folder_id
            
            # Create folder
            folder_metadata = {
                'name': self.root_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"📁 Root folder created: {self.root_folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error ensuring root folder: {e}")
            raise
    
    def scan_and_move(self):
        """Scan directories and move old files to Drive."""
        logger.info(f"🔍 Scanning {len(self.directories)} directories...")
        
        for directory in self.directories:
            self._process_directory(directory)
        
        # Summary
        logger.info(f"✅ Scan complete: {self.stats}")
        return self.stats
    
    def _process_directory(self, directory: str):
        """Process a single directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            self.stats['details'].append({
                'status': 'NOT_FOUND',
                'directory': directory,
                'count': 0
            })
            return
        
        logger.info(f"📂 Processing: {directory}")
        
        # Find files older than max_age_days
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        aged_files = []
        
        for file_path in dir_path.glob('**/*'):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    aged_files.append(file_path)
        
        if not aged_files:
            self.stats['details'].append({
                'status': 'NO_FILES',
                'directory': directory,
                'count': 0
            })
            logger.info(f"   No aged files in {directory}")
            return
        
        logger.info(f"   Found {len(aged_files)} aged files")
        
        # Process files
        for file_path in aged_files:
            self._archive_file(file_path)
    
    def _archive_file(self, file_path: Path):
        """Archive a single file to Drive."""
        try:
            file_size = file_path.stat().st_size
            file_name = file_path.name
            
            logger.info(f"   📤 Archiving: {file_name} ({file_size / 1024:.1f} KB)")
            
            # Upload to Drive
            media = MediaFileUpload(str(file_path), resumable=True)
            file_metadata = {
                'name': file_name,
                'parents': [self.root_folder_id]
            }
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name'
            ).execute()
            
            file_id = file.get('id')
            self.stats['uploaded_file_ids'].append(file_id)
            self.stats['successful'] += 1
            self.stats['total_files_archived'] += 1
            
            # Delete local file
            file_path.unlink()
            
            logger.info(f"   ✅ Uploaded: {file_name} (ID: {file_id})")
            
        except Exception as e:
            logger.error(f"   ❌ Failed to archive {file_path.name}: {e}")
            self.stats['failed'] += 1
            
            # Move to fallback
            try:
                fallback_path = Path(self.fallback_dir) / file_path.name
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(fallback_path))
                self.stats['fallback'] += 1
                logger.info(f"   📁 Moved to fallback: {fallback_path}")
            except Exception as e2:
                logger.error(f"   ❌ Fallback failed: {e2}")


def main():
    """Run Janitor Agent."""
    logging.basicConfig(level=logging.INFO)
    
    janitor = JanitorAgent(
        max_age_days=1,  # For testing - move files older than 1 day
        directories=[
            '/home/maxlo/PROMETHEUS/downloads',
            '/home/maxlo/PROMETHEUS/evidence',
            '/home/maxlo/PROMETHEUS/compressed'
        ]
    )
    
    stats = janitor.scan_and_move()
    
    print("\n" + "="*70)
    print(" JANITOR AGENT - SUMMARY")
    print("="*70)
    print(f"   Directories scanned: {len(janitor.directories)}")
    print(f"   Files archived: {stats['successful']}")
    print(f"   Files failed: {stats['failed']}")
    print(f"   Fallback: {stats['fallback']}")
    print(f"   Uploaded file IDs: {len(stats['uploaded_file_ids'])}")
    print("="*70)


if __name__ == "__main__":
    main()
