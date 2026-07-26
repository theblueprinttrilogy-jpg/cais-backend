#!/usr/bin/env python3
"""
Google Drive Explorer - Interactive file explorer for Google Drive.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import hashlib

@dataclass
class GDriveFile:
    """Represents a file in Google Drive."""
    id: str
    name: str
    mime_type: str
    size: int
    modified_time: str
    web_view_link: str
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'mime_type': self.mime_type,
            'size': self.size,
            'modified_time': self.modified_time,
            'web_view_link': self.web_view_link,
            'parent_id': self.parent_id
        }

class GDriveExplorer:
    """
    Interactive Google Drive explorer with search and categorization.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the GDrive explorer.
        
        Args:
            credentials_path: Path to the service account credentials.
        """
        self.credentials_path = credentials_path
        self.service = None
        self.current_folder_id = 'root'
        self.current_folder_path = '/'
        self.categories: Dict[str, List[str]] = {}
        self.category_file = Path('~/PROMETHEUS/data/categories/categories.json').expanduser()
        self.category_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._load_categories()
        self._init_service()
    
    def _init_service(self):
        """Initialize the Google Drive service."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            if self.credentials_path:
                creds_path = Path(self.credentials_path).expanduser()
            else:
                creds_path = Path('~/PROMETHEUS/config/security/gdrive-credentials.json').expanduser()
            
            if not creds_path.exists():
                print(f"⚠️ Credentials file not found: {creds_path}")
                print("   Please place your service account JSON file at this location.")
                return
            
            creds = service_account.Credentials.from_service_account_file(
                str(creds_path),
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            self.service = build('drive', 'v3', credentials=creds)
            print("✅ Google Drive service initialized")
            
        except Exception as e:
            print(f"❌ Error initializing Drive service: {e}")
    
    def _load_categories(self):
        """Load categories from file."""
        if self.category_file.exists():
            with open(self.category_file, 'r') as f:
                self.categories = json.load(f)
    
    def _save_categories(self):
        """Save categories to file."""
        with open(self.category_file, 'w') as f:
            json.dump(self.categories, f, indent=2)
    
    def _list_files(self, folder_id: Optional[str] = None, query: Optional[str] = None) -> List[GDriveFile]:
        """
        List files in a folder or matching a search query.
        """
        if not self.service:
            print("❌ Drive service not initialized")
            return []
        
        folder_id = folder_id or self.current_folder_id
        
        q_parts = ["trashed=false"]
        if folder_id != 'root':
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"(name contains '{query}' or fullText contains '{query}')")
        
        q = " and ".join(q_parts)
        
        try:
            response = self.service.files().list(
                q=q,
                spaces='drive',
                fields='files(id, name, mimeType, size, modifiedTime, webViewLink, parents)',
                pageSize=100
            ).execute()
            
            files = []
            for f in response.get('files', []):
                gfile = GDriveFile(
                    id=f['id'],
                    name=f['name'],
                    mime_type=f.get('mimeType', ''),
                    size=int(f.get('size', 0)),
                    modified_time=f.get('modifiedTime', ''),
                    web_view_link=f.get('webViewLink', ''),
                    parent_id=f.get('parents', [''])[0] if f.get('parents') else None
                )
                files.append(gfile)
            
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def display_files(self, files: List[GDriveFile]):
        """Display files in a formatted list."""
        if not files:
            print("📂 No files found.")
            return
        
        print(f"\n📁 {self.current_folder_path}")
        print("="*60)
        print(f"{'Type':<4} {'Name':<40} {'Size':<12} {'Modified':<20}")
        print("-"*60)
        
        for f in files:
            if f.mime_type == 'application/vnd.google-apps.folder':
                icon = "📁"
            elif f.mime_type == 'application/pdf':
                icon = "📄"
            elif f.mime_type.startswith('image/'):
                icon = "🖼️"
            else:
                icon = "📎"
            
            if f.size < 1024:
                size_str = f"{f.size} B"
            elif f.size < 1024 * 1024:
                size_str = f"{f.size / 1024:.1f} KB"
            else:
                size_str = f"{f.size / (1024 * 1024):.1f} MB"
            
            print(f"{icon:<4} {f.name[:40]:<40} {size_str:<12} {f.modified_time[:16]:<20}")
    
    def run_interactive(self):
        """Run the interactive explorer."""
        print("\n" + "="*60)
        print("🔍 Google Drive Explorer")
        print("="*60)
        print("\nCommands:")
        print("  ls           - List files in current folder")
        print("  cd <name>    - Enter folder")
        print("  ..           - Go up one level")
        print("  search <q>   - Search files")
        print("  cat <name>   - Categorize files in current folder")
        print("  show-cats    - Show categories")
        print("  exit         - Exit")
        print("="*60)
        
        while True:
            cmd = input(f"\n📁 {self.current_folder_path} > ").strip()
            
            if cmd == 'exit':
                break
            elif cmd == 'ls':
                files = self._list_files()
                self.display_files(files)
            elif cmd == '..':
                self._go_up()
            elif cmd.startswith('cd '):
                folder_name = cmd[3:].strip()
                self._enter_folder(folder_name)
            elif cmd.startswith('search '):
                query = cmd[7:].strip()
                print(f"🔍 Searching for: {query}")
                files = self._list_files(query=query)
                self.display_files(files)
            elif cmd.startswith('cat '):
                category_name = cmd[4:].strip()
                self._categorize_interactive(category_name)
            elif cmd == 'show-cats':
                self._show_categories()
            else:
                print(f"❌ Unknown command: {cmd}")
    
    def _enter_folder(self, folder_name: str):
        """Enter a folder by name."""
        files = self._list_files(self.current_folder_id)
        for f in files:
            if f.name == folder_name and f.mime_type == 'application/vnd.google-apps.folder':
                self.current_folder_id = f.id
                self.current_folder_path = os.path.join(self.current_folder_path, folder_name)
                print(f"📁 Entered: {self.current_folder_path}")
                return
        
        print(f"❌ Folder '{folder_name}' not found.")
    
    def _go_up(self):
        """Go up one folder level."""
        if self.current_folder_id != 'root':
            try:
                response = self.service.files().get(
                    fileId=self.current_folder_id,
                    fields='parents'
                ).execute()
                
                parents = response.get('parents', [])
                if parents:
                    self.current_folder_id = parents[0]
                    path_parts = self.current_folder_path.strip('/').split('/')
                    if path_parts:
                        path_parts.pop()
                        self.current_folder_path = '/' + '/'.join(path_parts) if path_parts else '/'
                    print(f"📁 Up to: {self.current_folder_path}")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _categorize_interactive(self, category_name: str):
        """Interactive categorization of files."""
        files = self._list_files()
        if not files:
            print("No files in current folder.")
            return
        
        print(f"\n📂 Categorizing files as: {category_name}")
        
        selected_ids = []
        for i, f in enumerate(files):
            if f.mime_type == 'application/vnd.google-apps.folder':
                continue
            
            print(f"\n  [{i+1}/{len(files)}] {f.name}")
            response = input(f"    Add to '{category_name}'? (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                selected_ids.append(f.id)
                print("    ✅ Added")
            else:
                print("    ⏭️ Skipped")
        
        if selected_ids:
            if category_name not in self.categories:
                self.categories[category_name] = []
            self.categories[category_name].extend(selected_ids)
            self._save_categories()
            print(f"\n✅ Added {len(selected_ids)} files to '{category_name}'")
        else:
            print("No files added.")
    
    def _show_categories(self):
        """Show all categories."""
        if not self.categories:
            print("No categories defined.")
            return
        
        print("\n📂 Categories:")
        print("="*40)
        for name, file_ids in self.categories.items():
            print(f"  {name}: {len(file_ids)} files")
