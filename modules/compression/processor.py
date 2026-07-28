"""
Compression Processor for CAIS
Compresses downloaded files intelligently based on file type.
"""

import os
import zipfile
import gzip
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class CompressionProcessor:
    """Compresses files based on their type."""
    
    def __init__(self, output_dir: str = "./compressed"):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_directory(self, directory_path: str) -> Dict:
        """Process all files in a directory."""
        input_dir = Path(directory_path).expanduser()
        
        if not input_dir.exists():
            return {'success': False, 'error': f'Directory not found: {directory_path}'}
        
        files = list(input_dir.glob('*'))
        files = [f for f in files if f.is_file()]
        
        print(f"\n Processing {len(files)} files...")
        print("-" * 50)
        
        processed = 0
        
        # Create ZIP archive
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.output_dir / f"cais_compressed_{timestamp}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                arcname = file_path.name
                zipf.write(file_path, arcname)
                processed += 1
                original_size = file_path.stat().st_size / (1024 * 1024)
                print(f"   {file_path.name} ({original_size:.2f} MB) -> compressed")
        
        compressed_size = archive_path.stat().st_size / (1024 * 1024)
        
        print("-" * 50)
        print(f"\n COMPRESSION COMPLETE:")
        print(f"   Files processed: {processed}")
        print(f"   Archive size: {compressed_size:.2f} MB")
        print(f"   Archive: {archive_path}")
        
        return {
            'success': True,
            'processed': processed,
            'archive': str(archive_path),
            'archive_size_mb': compressed_size
        }
