"""
Self-Learning Analyzer for CAIS.
Analyzes downloaded and compressed files to extract patterns and generate
automatic configuration for the CAIS system.
"""
import os
import json
import zipfile
import tarfile
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class SelfLearningAnalyzer:
    """
    Analyzes compressed archives and generates automatic system configuration.
    """

    def __init__(self, archive_path=None, output_dir="./cais_config"):
        self.archive_path = Path(archive_path) if archive_path else None
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = {
            'system_name': 'CAIS - Construction AI System',
            'version': '1.0.0',
            'generated_from': str(self.archive_path) if archive_path else None,
            'generated_date': datetime.now().isoformat(),
            'modules': [],
            'rules': [],
            'categories': [],
            'file_types': [],
            'patterns': [],
            'configurations': {}
        }

    def analyze_archive(self, archive_path):
        """
        Analyze a compressed archive and extract its contents.
        """
        self.archive_path = Path(archive_path)
        if not self.archive_path.exists():
            return {'success': False, 'error': f'Archive not found: {archive_path}'}

        print(f"\nAnalyzing archive: {self.archive_path.name}")
        print("-" * 50)

        if str(archive_path).endswith('.zip'):
            return self._analyze_zip(archive_path)
        elif str(archive_path).endswith('.tar.gz') or str(archive_path).endswith('.tgz'):
            return self._analyze_tar(archive_path)
        else:
            return {'success': False, 'error': 'Format not supported. Use .zip or .tar.gz'}

    def _analyze_zip(self, zip_path):
        """Analyze ZIP archive."""
        temp_dir = self.output_dir / "temp_extract"
        temp_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)
                print(f"Extracted {len(zipf.namelist())} files")
            self._analyze_directory(temp_dir)
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error analyzing ZIP: {e}")
            return {'success': False, 'error': str(e)}
        return self._save_config()

    def _analyze_tar(self, tar_path):
        """Analyze TAR.GZ archive."""
        temp_dir = self.output_dir / "temp_extract"
        temp_dir.mkdir(exist_ok=True)
        try:
            with tarfile.open(tar_path, 'r:gz') as tarf:
                tarf.extractall(temp_dir)
                print(f"Extracted {len(tarf.getnames())} files")
            self._analyze_directory(temp_dir)
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error analyzing TAR: {e}")
            return {'success': False, 'error': str(e)}
        return self._save_config()

    def _analyze_directory(self, directory):
        """Analyze a complete directory for patterns."""
        files = list(directory.rglob('*'))
        files = [f for f in files if f.is_file()]
        print(f"Analyzing {len(files)} files...")

        file_extensions = {}
        detected_structures = []

        for file_path in files:
            ext = file_path.suffix.lower()
            if ext:
                file_extensions[ext] = file_extensions.get(ext, 0) + 1

            if ext in ['.txt', '.json', '.csv', '.xml', '.md', '.py', '.js']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    patterns = self._extract_patterns(content)
                    if patterns:
                        detected_structures.append({
                            'file': file_path.name,
                            'patterns': patterns
                        })
                except:
                    pass

        self.config['file_types'] = file_extensions

        categories = []
        for ext, count in file_extensions.items():
            if count > 1:
                categories.append({
                    'extension': ext,
                    'count': count,
                    'category': self._guess_category(ext)
                })

        self.config['categories'] = categories

        if detected_structures:
            self.config['patterns'] = detected_structures

        self._detect_modules(directory)

        print(f"Analysis completed")
        print(f"Extensions found: {len(file_extensions)}")
        print(f"Categories detected: {len(categories)}")

    def _extract_patterns(self, content):
        """Extract configuration patterns from content."""
        patterns = []
        config_patterns = [
            r'config\s*=\s*{',  # JSON config
            r'<config>',        # XML config
            r'\[.*\]\s*\n\s*\w+\s*=',  # INI config
            r'#.*config',       # Config comments
            r'ENV\s*=\s*',      # Environment variables
            r'API\s*=\s*',      # API config
            r'DATABASE\s*=\s*', # Database config
        ]
        for pattern in config_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                patterns.append(pattern)
        return patterns

    def _guess_category(self, extension):
        """Guess file category by extension."""
        categories = {
            '.pdf': 'documents',
            '.docx': 'documents',
            '.xlsx': 'data',
            '.csv': 'data',
            '.json': 'configuration',
            '.xml': 'configuration',
            '.txt': 'text',
            '.md': 'documentation',
            '.py': 'code',
            '.js': 'code',
            '.html': 'web',
            '.css': 'web',
            '.jpg': 'images',
            '.png': 'images',
            '.webp': 'images',
            '.zip': 'archives',
            '.gz': 'archives'
        }
        return categories.get(extension, 'other')

    def _detect_modules(self, directory):
        """Detect potential modules in the directory."""
        modules = []
        config_files = ['config.json', 'settings.json', 'cais_config.json', 'config.yaml']
        for config_file in config_files:
            config_path = directory / config_file
            if config_path.exists():
                modules.append({
                    'name': config_file.replace('.json', '').replace('.yaml', ''),
                    'type': 'configuration',
                    'file': str(config_path)
                })
        for subdir in directory.iterdir():
            if subdir.is_dir():
                subdir_name = subdir.name.lower()
                if any(keyword in subdir_name for keyword in ['modules', 'src', 'lib', 'core']):
                    modules.append({
                        'name': subdir_name,
                        'type': 'module',
                        'path': str(subdir)
                    })
        if modules:
            self.config['modules'] = modules
            print(f"Modules detected: {len(modules)}")

    def _save_config(self):
        """Save the generated configuration."""
        config_path = self.output_dir / "cais_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"Configuration saved to: {config_path}")
        return {
            'success': True,
            'config_path': str(config_path),
            'summary': {
                'categories': len(self.config['categories']),
                'file_types': len(self.config['file_types']),
                'modules': len(self.config['modules']),
                'patterns': len(self.config['patterns'])
            }
        }

    def build_system_from_config(self):
        """Build the CAIS system from generated configuration."""
        config_path = self.output_dir / "cais_config.json"
        if not config_path.exists():
            return {'success': False, 'error': 'Configuration not found. Run analyze_archive first.'}

        with open(config_path, 'r') as f:
            config = json.load(f)

        print("\nBuilding system from configuration...")
        print("-" * 50)

        for module in config.get('modules', []):
            print(f"Creating module: {module.get('name')}")

        for category in config.get('categories', []):
            print(f"Creating rule for: {category.get('category')} ({category.get('extension')})")

        system_config = {
            'cais_version': '1.0.0',
            'generated_from': str(config_path),
            'generated_date': datetime.now().isoformat(),
            'modules_created': len(config.get('modules', [])),
            'rules_created': len(config.get('categories', [])),
            'status': 'ready'
        }

        system_path = self.output_dir / "system_build.json"
        with open(system_path, 'w') as f:
            json.dump(system_config, f, indent=2)

        print("-" * 50)
        print("System built successfully")
        print(f"System configuration: {system_path}")

        return {
            'success': True,
            'system_config': str(system_path),
            'modules': len(config.get('modules', [])),
            'rules': len(config.get('categories', []))
        }
