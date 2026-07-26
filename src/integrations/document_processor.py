#!/usr/bin/env python3
"""
Document Processor - Procesa documentos descargados
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import PyPDF2

class DocumentProcessor:
    """
    Procesa documentos para extraer metadatos y contenido.
    """
    
    def __init__(self, output_dir: str = "~/PROMETHEUS/output/processed"):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file."""
        print(f"📄 Processing: {file_path.name}")
        
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        result = {
            'filename': file_path.name,
            'path': str(file_path),
            'size': file_path.stat().st_size,
            'hash': file_hash,
            'extension': file_path.suffix.lower(),
            'processed_at': datetime.now().isoformat(),
            'content': None,
            'metadata': {},
            'success': False,
            'error': None
        }
        
        # Process PDFs
        if file_path.suffix.lower() == '.pdf':
            try:
                content, metadata = self._process_pdf(file_path)
                result['content'] = content
                result['metadata'] = metadata
                result['success'] = True
            except Exception as e:
                result['error'] = str(e)
        else:
            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                result['content'] = content[:1000]
                result['success'] = True
            except Exception as e:
                result['error'] = f"Unsupported format: {file_path.suffix}"
        
        return result
    
    def _process_pdf(self, file_path: Path) -> tuple:
        """Process PDF file."""
        content = ""
        metadata = {}
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                }
            
            for page in reader.pages:
                content += page.extract_text() + "\n"
            
            metadata['page_count'] = len(reader.pages)
        
        return content, metadata
    
    def process_directory(self, directory_path: str) -> List[Dict]:
        """Process all files in a directory."""
        results = []
        directory = Path(directory_path).expanduser()
        
        if not directory.exists():
            print(f"❌ Directory not found: {directory_path}")
            return results
        
        files = [f for f in directory.iterdir() if f.is_file()]
        
        for i, file_path in enumerate(files):
            print(f"  [{i+1}/{len(files)}] {file_path.name}")
            result = self.process_file(file_path)
            results.append(result)
        
        # Save results
        output_path = self.output_dir / f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to: {output_path}")
        return results
