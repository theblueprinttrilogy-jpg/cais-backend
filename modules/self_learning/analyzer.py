"""
Self-Learning Analyzer for CAIS
Analyzes downloaded files and generates system configuration.
"""

import os
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class SelfLearningAnalyzer:
    """Analyzes files and generates configuration."""
    
    def __init__(self, archive_path: str = None, output_dir: str = "./cais_config"):
        self.archive_path = Path(archive_path).expanduser() if archive_path else None
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_archive(self, archive_path: str) -> Dict:
        """Analyze a compressed archive."""
        archive = Path(archive_path).expanduser()
        
        if not archive.exists():
            return {'success': False, 'error': f'Archive not found: {archive_path}'}
        
        print(f"\n ANALYZING ARCHIVE: {archive.name}")
        print("-" * 50)
        
        # Extract to temp directory
        temp_dir = self.output_dir / "temp_extract"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(archive, 'r') as zipf:
                zipf.extractall(temp_dir)
                print(f"   Extracted {len(zipf.namelist())} files")
            
            # Analyze files
            files = list(temp_dir.glob('*'))
            files = [f for f in files if f.is_file()]
            
            file_types = {}
            for f in files:
                ext = f.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            
            # Generate configuration
            config = {
                'system_name': 'CAIS - Construction AI System',
                'version': '1.0.0',
                'generated_from': str(archive),
                'generated_date': datetime.now().isoformat(),
                'file_types': file_types,
                'categories': [
                    {'extension': ext, 'count': count, 'category': 'documents'}
                    for ext, count in file_types.items()
                ],
                'total_files': len(files),
                'modules': []
            }
            
            # Save config
            config_path = self.output_dir / 'cais_config.json'
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Cleanup temp
            import shutil
            shutil.rmtree(temp_dir)
            
            print(f"\n ANALYSIS COMPLETE:")
            print(f"   File types found: {len(file_types)}")
            print(f"   Total files: {len(files)}")
            print(f"   Config saved: {config_path}")
            
            return {
                'success': True,
                'config_path': str(config_path),
                'summary': {
                    'file_types': len(file_types),
                    'total_files': len(files),
                    'categories': len(config['categories'])
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
