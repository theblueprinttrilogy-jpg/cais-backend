#!/usr/bin/env python3
"""
Janitor Agent - OAUTH VERSION for caiscodecompliance@gmail.com
Uses OAuth 2.0 with user credentials for Drive uploads.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import shutil
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
DEFAULT_MAX_AGE_DAYS = 45
DEFAULT_ROOT_FOLDER_NAME = "JACINTO_CORREA_COMPUTER"


class JanitorOAuth:
    """Janitor Agent using OAuth 2.0 with caiscodecompliance@gmail.com"""
    
    def __init__(
        self,
        credentials_file: str = "secrets/oauth_credentials.json",
        token_file: str = "secrets/token.pickle",
        root_folder_name: str = DEFAULT_ROOT_FOLDER_NAME,
        fallback_dir: str = "/tmp/cais_janitor_fallback",
        max_age_days: int = 1,
        directories: List[str] = None
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.root_folder_name = root_folder_name
        self.fallback_dir = fallback_dir
        self.max_age_days = max_age_days
        self.directories = directories or [
            '/home/maxlo/PROMETHEUS/downloads',
            '/home/maxlo/PROMETHEUS/evidence',
            '/home/maxlo/PROMETHEUS/compressed',
            '/home/maxlo/PROMETHEUS/logs',
            '/home/maxlo/PROMETHEUS/output',
            '/home/maxlo/PROMETHEUS/reports'
            
        ]
        
        self.service = self._build_service()
        self.user_email = "caiscodecompliance@gmail.com"
        self.root_folder_id = self._ensure_root_folder()
        
        self.stats = {
            'successful': 0,
            'failed': 0,
            'fallback': 0,
            'total_files_archived': 0,
            'uploaded_file_ids': []
        }
        
        logger.info(f"✅ JanitorOAuth initialized: {self.user_email}")
    
    def _build_service(self):
        """Build Drive service with OAuth 2.0."""
        creds = None
        
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("✅ Token refreshed")
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"OAuth credentials not found: {self.credentials_file}\n"
                        "Create OAuth credentials at: "
                        "https://console.cloud.google.com/apis/credentials"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("✅ OAuth authentication successful")
            
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def _ensure_root_folder(self) -> str:
        """Ensure root folder exists."""
        try:
            results = self.service.files().list(
                q=f"name='{self.root_folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"📁 Root folder found: {self.root_folder_name}")
                return folder_id
            
            folder_metadata = {
                'name': self.root_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=folder_metadata, fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"📁 Root folder created: {self.root_folder_name}")
            return folder_id
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise
    
    def scan_and_move(self):
        """Scan and move old files."""
        logger.info(f"🔍 Scanning {len(self.directories)} directories...")
        
        for directory in self.directories:
            self._process_directory(directory)
        
        logger.info(f"\n📊 COMPLETE: {self.stats['successful']} files archived")
        return self.stats
    
    def _process_directory(self, directory: str):
        """Process a directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"⚠️ Directory not found: {directory}")
            return
        
        logger.info(f"📂 Processing: {directory}")
        
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        aged_files = []
        
        for file_path in dir_path.glob('**/*'):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    aged_files.append(file_path)
        
        if not aged_files:
            logger.info(f"   No aged files in {directory}")
            return
        
        logger.info(f"   Found {len(aged_files)} aged files")
        for file_path in aged_files:
            self._archive_file(file_path)
    
    def _archive_file(self, file_path: Path):
        """Archive a single file."""
        try:
            file_size = file_path.stat().st_size
            file_name = file_path.name
            
            logger.info(f"   📤 Archiving: {file_name} ({file_size / 1024:.1f} KB)")
            
            if file_size > 100 * 1024 * 1024:
                logger.warning(f"   ⚠️ File too large: {file_name}")
                self.stats['failed'] += 1
                return
            
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
            
            file_path.unlink()
            logger.info(f"   ✅ Uploaded: {file_name}")
            
        except Exception as e:
            logger.error(f"   ❌ Failed: {e}")
            self.stats['failed'] += 1
            
            try:
                fallback_path = Path(self.fallback_dir) / file_path.name
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(fallback_path))
                self.stats['fallback'] += 1
            except Exception as e2:
                logger.error(f"   ❌ Fallback failed: {e2}")


def main():
    print("\n" + "="*70)
    print(" JANITOR AGENT - OAUTH")
    print(f" Account: caiscodecompliance@gmail.com")
    print("="*70)
    
    janitor = JanitorOAuth(
        credentials_file="secrets/oauth_credentials.json",
        max_age_days=1
    )
    
    stats = janitor.scan_and_move()
    
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    print(f"   Uploaded: {stats['successful']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Fallback: {stats['fallback']}")
    print("="*70)


if __name__ == "__main__":
    main()
