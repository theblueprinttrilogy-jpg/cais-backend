#!/usr/bin/env python3
"""
Storage Agent - CAIS
Compresses, classifies, renames files and stores results in Google Drive.
Account: theblueprinttrilogy@gmail.com
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import sys
import json
import zipfile
import gzip
import shutil
import hashlib
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re

# Google Drive
from modules.google_drive.connector import GoogleDriveConnector
from modules.google_drive.downloader import GoogleDriveDownloader

# Compression
from modules.compression.processor import CompressionProcessor


@dataclass
class StorageResult:
    """Result from storage operation."""
    file_name: str
    original_path: str
    compressed_path: str
    renamed_path: str
    classification: str
    drive_file_id: str
    hash: str
    size_bytes: int
    uploaded: bool


class CompressorAgent:
    """
    Agent 1: Compressor Agent
    Compresses evidence files using intelligent compression.
    """
    
    def __init__(self, output_dir: str = "./compressed"):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.processor = CompressionProcessor(output_dir=str(self.output_dir))
    
    def compress_file(self, file_path: str) -> str:
        """
        Compress a single file.
        """
        file_path = Path(file_path).expanduser()
        
        if not file_path.exists():
            print(f"   ⚠️ File not found: {file_path}")
            return ""
        
        # Determine compression method by extension
        ext = file_path.suffix.lower()
        compressed_path = self.output_dir / file_path.name
        
        if ext in ['.png', '.jpg', '.jpeg', '.pdf']:
            # Use ZIP for images and PDFs
            zip_path = self.output_dir / f"{file_path.stem}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, file_path.name)
            return str(zip_path)
        
        elif ext in ['.txt', '.json', '.csv', '.xml']:
            # Use GZIP for text files
            gz_path = self.output_dir / f"{file_path.name}.gz"
            with open(file_path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return str(gz_path)
        
        else:
            # Copy as is
            shutil.copy2(file_path, compressed_path)
            return str(compressed_path)
    
    def compress_directory(self, directory_path: str) -> str:
        """
        Compress an entire directory.
        """
        return self.processor.process_directory(directory_path).get('archive', '')


class ClassifierAgent:
    """
    Agent 2: Classifier Agent
    Classifies files by type, severity, and jurisdiction.
    """
    
    CLASSIFICATIONS = {
        'redbox': 'violation_evidence',
        'yellow_highlight': 'code_evidence',
        'inspection_report': 'report',
        'violation': 'violation_evidence',
        'code': 'code_reference',
        'default': 'other'
    }
    
    def __init__(self):
        self.classified_files: Dict[str, List[str]] = {
            'violation_evidence': [],
            'code_evidence': [],
            'report': [],
            'other': []
        }
    
    def classify_file(self, file_path: str) -> str:
        """
        Classify a single file based on its name and content.
        """
        file_path = Path(file_path).expanduser()
        file_name = file_path.name.lower()
        
        if 'redbox' in file_name or 'violation' in file_name:
            return 'violation_evidence'
        elif 'yellow_highlight' in file_name or 'code' in file_name:
            return 'code_evidence'
        elif 'report' in file_name or 'inspection' in file_name:
            return 'report'
        else:
            return 'other'
    
    def classify_directory(self, directory_path: str) -> Dict[str, List[str]]:
        """
        Classify all files in a directory.
        """
        directory_path = Path(directory_path).expanduser()
        
        for file_path in directory_path.glob('*'):
            if file_path.is_file():
                classification = self.classify_file(str(file_path))
                self.classified_files[classification].append(str(file_path))
        
        return self.classified_files
    
    def get_classification_summary(self) -> Dict:
        """
        Get summary of classified files.
        """
        return {
            cat: len(files) for cat, files in self.classified_files.items()
        }


class RenamerAgent:
    """
    Agent 3: Renamer Agent
    Renames files with standard format: JURISDICTION_CODE_PAGE_TIMESTAMP
    """
    
    def __init__(self, jurisdiction: str = 'Florida'):
        self.jurisdiction = jurisdiction
        self.rename_count = 0
    
    def rename_file(self, file_path: str, code_id: str = '', page_number: int = 0) -> str:
        """
        Rename a file with standard format.
        
        Format: JURISDICTION_CODE_PAGE_TIMESTAMP.ext
        Example: Florida_FBC1609.1.1_P03_20260727_185001.png
        """
        file_path = Path(file_path).expanduser()
        
        if not file_path.exists():
            print(f"   ⚠️ File not found: {file_path}")
            return ""
        
        # Build new name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code_part = code_id.replace('.', '_') if code_id else 'UNKNOWN'
        page_part = f"P{page_number:03d}" if page_number > 0 else "P000"
        
        new_name = f"{self.jurisdiction}_{code_part}_{page_part}_{timestamp}{file_path.suffix}"
        new_path = file_path.parent / new_name
        
        # Rename
        try:
            file_path.rename(new_path)
            self.rename_count += 1
            return str(new_path)
        except Exception as e:
            print(f"   ⚠️ Error renaming: {e}")
            return str(file_path)
    
    def rename_batch(self, files: List[Dict]) -> List[str]:
        """
        Rename multiple files.
        """
        renamed_paths = []
        for file_info in files:
            new_path = self.rename_file(
                file_info.get('path', ''),
                file_info.get('code_id', ''),
                file_info.get('page', 0)
            )
            renamed_paths.append(new_path)
        
        return renamed_paths


class UploaderAgent:
    """
    Agent 4: Uploader Agent
    Uploads files to Google Drive (theblueprinttrilogy@gmail.com)
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or '/home/maxlo/cais_new/docker/credentials/service-account.json'
        self.connector = GoogleDriveConnector(credentials_path)
        self.uploaded_files: List[str] = []
    
    async def upload_file(self, file_path: str, folder_name: str = 'CAIS_Evidence') -> str:
        """
        Upload a single file to Google Drive.
        """
        from googleapiclient.http import MediaFileUpload
        
        file_path = Path(file_path).expanduser()
        
        if not file_path.exists():
            print(f"   ⚠️ File not found: {file_path}")
            return ""
        
        try:
            service = self.connector.get_service()
            
            # Find or create folder
            folder_id = self.connector.find_folder_by_name(folder_name)
            
            if not folder_id:
                # Create folder
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
                print(f"   📁 Created folder: {folder_name}")
            
            # Upload file
            media = MediaFileUpload(str(file_path), resumable=True)
            file_metadata = {
                'name': file_path.name,
                'parents': [folder_id]
            }
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            self.uploaded_files.append(str(file_path))
            
            print(f"   ✅ Uploaded: {file_path.name} (ID: {file_id[:8]}...)")
            return file_id
            
        except Exception as e:
            print(f"   ❌ Upload failed: {e}")
            return ""
    
    async def upload_batch(self, files: List[str], folder_name: str = 'CAIS_Evidence') -> List[str]:
        """
        Upload multiple files to Google Drive.
        """
        file_ids = []
        for file_path in files:
            file_id = await self.upload_file(file_path, folder_name)
            if file_id:
                file_ids.append(file_id)
        
        return file_ids
    
    async def create_structured_folders(self, jurisdiction: str, audit_id: str) -> str:
        """
        Create structured folders in Google Drive.
        """
        base_folder = f"CAIS_{jurisdiction}_{audit_id}"
        
        subfolders = [
            f"{base_folder}/Violations",
            f"{base_folder}/Codes",
            f"{base_folder}/Reports",
            f"{base_folder}/Compressed"
        ]
        
        created_folders = []
        service = self.connector.get_service()
        
        for folder_name in subfolders:
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            created_folders.append(folder.get('id'))
            print(f"   📁 Created: {folder_name}")
        
        return created_folders[0] if created_folders else ""


class StorageAgent:
    """
    Storage Agent - Complete storage system.
    Coordinates all 4 storage sub-agents.
    """
    
    def __init__(self, jurisdiction: str = 'Florida'):
        self.jurisdiction = jurisdiction
        self.db_config = {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        # Initialize sub-agents
        self.compressor = CompressorAgent()
        self.classifier = ClassifierAgent()
        self.renamer = RenamerAgent(jurisdiction)
        self.uploader = UploaderAgent()
        
        self.stored_count = 0
        self.results: List[StorageResult] = []
    
    async def process_evidence(self, evidence_dir: str, audit_id: str) -> Dict:
        """
        Process all evidence files in a directory.
        """
        print(f"\n📦 STORAGE AGENT - Processing evidence...")
        print("=" * 50)
        
        evidence_path = Path(evidence_dir).expanduser()
        
        if not evidence_path.exists():
            return {'error': 'Evidence directory not found'}
        
        # 1. Classify files
        print("\n[1/4] CLASSIFYING FILES...")
        classified = self.classifier.classify_directory(str(evidence_path))
        classification_summary = self.classifier.get_classification_summary()
        print(f"   ✅ Classified: {classification_summary}")
        
        # 2. Rename files
        print("\n[2/4] RENAMING FILES...")
        renamed_files = []
        
        # Process classified files
        for category, files in classified.items():
            for file_path in files:
                # Extract code and page from filename
                code_match = re.search(r'(FBC|IBC|NEC|CBC)_?(\d+\.\d+(?:\.\d+)?)', file_path)
                code_id = code_match.group(0) if code_match else 'UNKNOWN'
                
                page_match = re.search(r'page(\d+)', file_path.lower())
                page = int(page_match.group(1)) if page_match else 0
                
                new_path = self.renamer.rename_file(file_path, code_id, page)
                renamed_files.append({
                    'original': file_path,
                    'renamed': new_path,
                    'category': category,
                    'code_id': code_id,
                    'page': page
                })
        
        print(f"   ✅ Renamed: {len(renamed_files)} files")
        
        # 3. Compress files
        print("\n[3/4] COMPRESSING FILES...")
        compressed_files = []
        for file_info in renamed_files:
            compressed_path = self.compressor.compress_file(file_info['renamed'])
            if compressed_path:
                compressed_files.append({
                    **file_info,
                    'compressed': compressed_path
                })
        
        print(f"   ✅ Compressed: {len(compressed_files)} files")
        
        # 4. Upload to Google Drive
        print("\n[4/4] UPLOADING TO GOOGLE DRIVE...")
        print("   Account: theblueprinttrilogy@gmail.com")
        
        # Create structured folders
        folder_id = await self.uploader.create_structured_folders(self.jurisdiction, audit_id)
        
        # Upload files
        uploaded_ids = []
        for file_info in compressed_files:
            file_id = await self.uploader.upload_file(
                file_info['compressed'],
                f"CAIS_{self.jurisdiction}_{audit_id}/{file_info['category']}"
            )
            if file_id:
                uploaded_ids.append(file_id)
        
        print(f"   ✅ Uploaded: {len(uploaded_ids)} files")
        
        # 5. Store in database
        print("\n[5/5] STORING IN DATABASE...")
        await self._store_violations(compressed_files, audit_id)
        
        return {
            'audit_id': audit_id,
            'jurisdiction': self.jurisdiction,
            'classified': classification_summary,
            'renamed': len(renamed_files),
            'compressed': len(compressed_files),
            'uploaded': len(uploaded_ids),
            'drive_folder_id': folder_id
        }
    
    async def _store_violations(self, files: List[Dict], audit_id: str):
        """
        Store violations in the database.
        """
        conn = await asyncpg.connect(**self.db_config)
        
        try:
            for file_info in files:
                if file_info['category'] == 'violation_evidence':
                    await conn.execute("""
                        INSERT INTO cais.violations 
                        (violation_id, audit_id, code_id, document_page, screenshot_path, severity, jurisdiction)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (violation_id) DO UPDATE SET
                            screenshot_path = EXCLUDED.screenshot_path
                    """,
                        f"VIO-{datetime.now().strftime('%Y%m%d')}-{self.stored_count+1:04d}",
                        audit_id,
                        file_info.get('code_id'),
                        file_info.get('page', 1),
                        file_info.get('compressed', ''),
                        'unknown',
                        self.jurisdiction
                    )
                    self.stored_count += 1
            
            # WORM entry
            await conn.execute("""
                INSERT INTO cais.worm_ledger 
                (sequence, event_type, payload, actor, previous_hash, node_id)
                SELECT 
                    COALESCE(MAX(sequence), -1) + 1,
                    'STORAGE_COMPLETE',
                    jsonb_build_object(
                        'audit_id', $1,
                        'files_stored', $2,
                        'jurisdiction', $3
                    ),
                    'storage_agent',
                    COALESCE(MAX(hash), '0' || REPEAT('0', 63)),
                    'local'
                FROM cais.worm_ledger
            """, audit_id, len(files), self.jurisdiction)
            
            print(f"   ✅ Database updated: {self.stored_count} violations stored")
            
        except Exception as e:
            print(f"   ❌ Database error: {e}")
        finally:
            await conn.close()
    
    async def get_statistics(self) -> Dict:
        """
        Get storage statistics.
        """
        conn = await asyncpg.connect(**self.db_config)
        try:
            total = await conn.fetchval("SELECT COUNT(*) FROM cais.violations")
            worm_count = await conn.fetchval("SELECT COUNT(*) FROM cais.worm_ledger")
            
            return {
                'total_violations': total,
                'worm_entries': worm_count,
                'storage_agent': 'active'
            }
            
        finally:
            await conn.close()


async def main():
    """Test the Storage Agent."""
    print("\n" + "="*70)
    print(" STORAGE AGENT - COMPLETE TEST")
    print(" Compressor + Classifier + Renamer + Uploader")
    print("="*70)
    
    agent = StorageAgent(jurisdiction='Florida')
    
    # Test with sample evidence
    evidence_dir = '/home/maxlo/PROMETHEUS/evidence'
    if Path(evidence_dir).exists():
        result = await agent.process_evidence(evidence_dir, 'TEST-001')
        print("\n" + "="*70)
        print(" STORAGE COMPLETE")
        print("="*70)
        for key, value in result.items():
            print(f"   {key}: {value}")
    else:
        print("❌ No evidence directory found")
        print("   Run Plan Inspector first to generate evidence.")


if __name__ == "__main__":
    asyncio.run(main())
