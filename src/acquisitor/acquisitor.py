#!/usr/bin/env python3
"""
Document Acquisitor - Downloads and compresses documents from Google Drive.
"""

import os
import json
import zipfile
import hashlib
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.integrations.gdrive_authenticator import GDriveAuthenticator
from src.integrations.category_manager import CategoryManager

@dataclass
class DownloadResult:
    """Result of a file download operation."""
    file_id: str
    file_name: str
    success: bool
    size: int = 0
    hash: str = ""
    error: str = ""

class Acquisitor:
    """
    Downloads and compresses documents from Google Drive by category.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the acquisitor.
        
        Args:
            credentials_path: Path to the service account credentials.
        """
        self.authenticator = GDriveAuthenticator(credentials_path)
        self.service = self.authenticator.get_service()
        
        self.download_dir = Path("~/PROMETHEUS/downloads").expanduser()
        self.compressed_dir = Path("~/PROMETHEUS/compressed").expanduser()
        self.log_dir = Path("~/PROMETHEUS/logs").expanduser()
        
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.compressed_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.category_manager = CategoryManager()
        self.max_concurrent_downloads = 5
        self.max_retries = 3
        self.retry_delay = 2
    
    def download_category(self, category_name: str, compress: bool = True) -> Dict:
        """
        Download all files in a category and optionally compress them.
        
        Args:
            category_name: Name of the category to download.
            compress: Whether to compress the files after download.
            
        Returns:
            Dict containing the results.
        """
        file_ids = self.category_manager.get_category(category_name)
        if not file_ids:
            print(f"❌ Category '{category_name}' not found or empty.")
            return {'success': False, 'error': 'Category not found'}
        
        print(f"\n📦 Downloading category: {category_name}")
        print(f"   Files: {len(file_ids)}")
        
        # Create category download directory
        category_download_dir = self.download_dir / category_name
        category_download_dir.mkdir(parents=True, exist_ok=True)
        
        # Download files
        results = self._download_files(file_ids, category_download_dir)
        
        # Log results
        self._log_download_results(category_name, results)
        
        # Compress if requested
        zip_path = None
        if compress:
            print("\n📦 Compressing files...")
            zip_path = self._compress_category(category_name, category_download_dir)
            
            if zip_path:
                # Clean up download directory
                shutil.rmtree(category_download_dir)
                print(f"✅ Cleaned up download directory")
        
        # Generate summary
        success_count = sum(1 for r in results if r.success)
        total_size = sum(r.size for r in results if r.success)
        
        return {
            'success': True,
            'category': category_name,
            'total_files': len(file_ids),
            'successful': success_count,
            'failed': len(results) - success_count,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'compressed': compress,
            'zip_path': str(zip_path) if zip_path else None
        }
    
    def _download_files(self, file_ids: List[str], output_dir: Path) -> List[DownloadResult]:
        """
        Download multiple files with concurrency.
        """
        results = []
        total = len(file_ids)
        
        for i, file_id in enumerate(file_ids, 1):
            print(f"  [{i}/{total}] Downloading...")
            result = self._download_file(file_id, output_dir)
            results.append(result)
            if result.success:
                print(f"    ✅ {result.file_name} ({result.size:,} bytes)")
            else:
                print(f"    ❌ Error: {result.error}")
        
        return results
    
    def _download_file(self, file_id: str, output_dir: Path, retry: int = 0) -> DownloadResult:
        """
        Download a single file from Google Drive.
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='name, size, mimeType'
            ).execute()
            
            file_name = file_metadata.get('name', file_id)
            
            # Skip Google Docs files that need export
            mime_type = file_metadata.get('mimeType', '')
            if mime_type.startswith('application/vnd.google-apps.'):
                return DownloadResult(
                    file_id=file_id,
                    file_name=file_name,
                    success=False,
                    error=f"Skipping Google Docs file"
                )
            
            # Prepare output path
            output_path = output_dir / file_name
            
            # Check if file already exists
            if output_path.exists():
                existing_size = output_path.stat().st_size
                expected_size = int(file_metadata.get('size', 0))
                if existing_size == expected_size:
                    return DownloadResult(
                        file_id=file_id,
                        file_name=file_name,
                        success=True,
                        size=existing_size,
                        hash=self._calculate_hash(output_path)
                    )
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            
            with open(output_path, 'wb') as f:
                try:
                    request.execute(f)
                except Exception as e:
                    if 'Requested range not satisfiable' in str(e):
                        f.write(b'')
            
            # Verify file
            if output_path.exists():
                size = output_path.stat().st_size
                expected_size = int(file_metadata.get('size', 0))
                
                if size == expected_size or expected_size == 0:
                    return DownloadResult(
                        file_id=file_id,
                        file_name=file_name,
                        success=True,
                        size=size,
                        hash=self._calculate_hash(output_path)
                    )
                else:
                    if retry < self.max_retries:
                        time.sleep(self.retry_delay * (retry + 1))
                        return self._download_file(file_id, output_dir, retry + 1)
                    
                    return DownloadResult(
                        file_id=file_id,
                        file_name=file_name,
                        success=False,
                        error=f"Size mismatch: {size} != {expected_size}"
                    )
            else:
                return DownloadResult(
                    file_id=file_id,
                    file_name=file_name,
                    success=False,
                    error="File not created"
                )
                
        except Exception as e:
            if retry < self.max_retries:
                time.sleep(self.retry_delay * (retry + 1))
                return self._download_file(file_id, output_dir, retry + 1)
            
            return DownloadResult(
                file_id=file_id,
                file_name=file_id,
                success=False,
                error=str(e)
            )
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(4096), b''):
                sha256.update(block)
        return sha256.hexdigest()
    
    def _compress_category(self, category_name: str, download_dir: Path) -> Optional[Path]:
        """
        Compress all files in a category download directory.
        """
        files = list(download_dir.glob('*'))
        if not files:
            print("No files to compress.")
            return None
        
        # Create ZIP file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name = f"{category_name}_{timestamp}.zip"
        zip_path = self.compressed_dir / zip_name
        
        print(f"   Compressing {len(files)} files...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                arcname = file_path.name
                zipf.write(file_path, arcname)
        
        # Calculate compression ratio
        original_size = sum(f.stat().st_size for f in files)
        compressed_size = zip_path.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        print(f"   ✅ Compressed: {zip_name}")
        print(f"      Original: {original_size / (1024 * 1024):.1f} MB")
        print(f"      Compressed: {compressed_size / (1024 * 1024):.1f} MB")
        print(f"      Savings: {ratio:.1f}%")
        
        return zip_path
    
    def _log_download_results(self, category_name: str, results: List[DownloadResult]):
        """Log download results to file."""
        log_file = self.log_dir / 'acquisitor.log'
        
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"CATEGORY: {category_name}\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
            f.write(f"{'='*60}\n")
            
            for r in results:
                status = "✅" if r.success else "❌"
                f.write(f"{status} {r.file_name} ({r.size:,} bytes)\n")
                if not r.success and r.error:
                    f.write(f"   ERROR: {r.error}\n")
            
            success = sum(1 for r in results if r.success)
            f.write(f"\nSUMMARY: {success}/{len(results)} files downloaded successfully\n")
