#!/usr/bin/env python3
"""
Janitor Agent - OAUTH DELEGATION VERSION
Uses user OAuth with domain-wide delegation to Google Drive.
Account: caiscodecompliance@gmail.com
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

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive']
DEFAULT_MAX_AGE_DAYS = 45
DEFAULT_ROOT_FOLDER_NAME = "JACINTO_CORREA_COMPUTER"


class JanitorAgentOAuth:
    """
    Janitor Agent using OAuth 2.0 with user credentials.
    Uses caiscodecompliance@gmail.com account.
    """
    
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
            '/home/maxlo/PROMETHEUS/compressed'
        ]
        
        # Build service with OAuth
        self.service = self._build_oauth_service()
        self.user_email = "caiscodecompliance@gmail.com"
        
        # Ensure root folder exists
        self.root_folder_id = self._ensure_root_folder()
        
        # Stats
        self.stats = {
            'successful': 0,
            'failed': 0,
            'fallback': 0,
            'total_files_archived': 0,
            'uploaded_file_ids': []
        }
        
        logger.info(f"✅ JanitorAgentOAuth initialized with: {self.user_email}")
    
    def _build_oauth_service(self):
        """Build service using OAuth 2.0 with user credentials."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("✅ Token refreshed")
            else:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"❌ OAuth credentials file not found: {self.credentials_file}")
                    logger.info("   Please create OAuth credentials in Google Cloud Console")
                    logger.info("   1. Go to: https://console.cloud.google.com/apis/credentials")
                    logger.info("   2. Create OAuth 2.0 Client ID")
                    logger.info("   3. Download JSON and save as: secrets/oauth_credentials.json")
                    raise FileNotFoundError(f"OAuth credentials not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("✅ OAuth authentication successful")
            
            # Save token
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def _ensure_root_folder(self) -> str:
        """Ensure root folder exists in Drive."""
        try:
            results = self.service.files().list(
                q=f"name='{self.root_folder_name}' and mimeType='application/vnd.google-apps.folder'",
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info(f"📁 Root folder found: {self.root_folder_name} (ID: {folder_id})")
                return folder_id
            
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
            logger.error(f"❌ Error: {e}")
            raise
    
    def scan_and_move(self):
        """Scan directories and move old files to Drive."""
        logger.info(f"🔍 Scanning {len(self.directories)} directories...")
        
        for directory in self.directories:
            self._process_directory(directory)
        
        logger.info(f"\n📊 SCAN COMPLETE:")
        logger.info(f"   Files archived: {self.stats['successful']}")
        logger.info(f"   Files failed: {self.stats['failed']}")
        logger.info(f"   Fallback: {self.stats['fallback']}")
        logger.info(f"   Uploaded: {len(self.stats['uploaded_file_ids'])}")
        
        return self.stats
    
    def _process_directory(self, directory: str):
        """Process a single directory."""
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
        """Archive a single file to Drive."""
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
            logger.info(f"   ✅ Uploaded: {file_name} (ID: {file_id[:8]}...)")
            
        except Exception as e:
            logger.error(f"   ❌ Failed: {e}")
            self.stats['failed'] += 1
            
            try:
                fallback_path = Path(self.fallback_dir) / file_path.name
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(fallback_path))
                self.stats['fallback'] += 1
                logger.info(f"   📁 Moved to fallback: {fallback_path}")
            except Exception as e2:
                logger.error(f"   ❌ Fallback failed: {e2}")


def main():
    print("\n" + "="*70)
    print(" JANITOR AGENT - OAUTH VERSION")
    print(" Account: caiscodecompliance@gmail.com")
    print("="*70)
    
    # Crear directorio de credenciales
    os.makedirs("secrets", exist_ok=True)
    
    janitor = JanitorAgentOAuth(
        credentials_file="secrets/oauth_credentials.json",
        max_age_days=1,
        directories=[
            '/home/maxlo/PROMETHEUS/downloads',
            '/home/maxlo/PROMETHEUS/evidence',
            '/home/maxlo/PROMETHEUS/compressed'
        ]
    )
    
    stats = janitor.scan_and_move()
    
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    print(f"   Files archived: {stats['successful']}")
    print(f"   Files failed: {stats['failed']}")
    print(f"   Fallback: {stats['fallback']}")
    print("="*70)


if __name__ == "__main__":
    main()
