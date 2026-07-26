#!/usr/bin/env python3
"""
Descargador Automático de Códigos de Construcción.
"""

import os
import re
import time
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

from src.parsers.code_sources import ALL_SOURCES, CodeSource


class CodeDownloader:
    """
    Descarga automática de códigos de construcción desde fuentes oficiales.
    """
    
    def __init__(self, output_dir: str = "~/PROMETHEUS/input/laws"):
        """
        Initialize the code downloader.
        
        Args:
            output_dir: Directory to save downloaded codes.
        """
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.download_log = self.output_dir / 'download_log.json'
        self.downloaded_files = self._load_log()
        
        # User agent para scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.max_retries = 3
        self.retry_delay = 5  # seconds
    
    def _load_log(self) -> Dict:
        """Load download log."""
        if self.download_log.exists():
            with open(self.download_log, 'r') as f:
                return json.load(f)
        return {'downloaded': [], 'failed': []}
    
    def _save_log(self):
        """Save download log."""
        with open(self.download_log, 'w') as f:
            json.dump(self.downloaded_files, f, indent=2)
    
    def download_codes(self, sources: Optional[List[CodeSource]] = None) -> Dict[str, Any]:
        """
        Download building codes from specified sources.
        
        Args:
            sources: List of sources to download. If None, downloads all.
            
        Returns:
            Dict with download results.
        """
        if sources is None:
            sources = ALL_SOURCES
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        print(f"📥 Starting download of {len(sources)} code sources...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_source = {
                executor.submit(self._download_source, source): source
                for source in sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                    if result['success']:
                        results['successful'].append(result['data'])
                        print(f"  ✅ Downloaded: {source.name} ({source.jurisdiction})")
                    else:
                        results['failed'].append({
                            'source': source.name,
                            'error': result.get('error', 'Unknown error')
                        })
                        print(f"  ❌ Failed: {source.name} - {result.get('error', 'Unknown error')}")
                except Exception as e:
                    results['failed'].append({
                        'source': source.name,
                        'error': str(e)
                    })
                    print(f"  ❌ Error downloading {source.name}: {e}")
        
        # Save results
        self.downloaded_files['downloaded'].extend(results['successful'])
        self.downloaded_files['failed'].extend(results['failed'])
        self._save_log()
        
        # Generate summary
        results['summary'] = {
            'total': len(sources),
            'successful': len(results['successful']),
            'failed': len(results['failed'])
        }
        
        return results
    
    def _download_source(self, source: CodeSource) -> Dict:
        """
        Download a single code source.
        
        Args:
            source: Code source to download.
            
        Returns:
            Dict with download result.
        """
        # Check if already downloaded
        filename = self._generate_filename(source)
        filepath = self.output_dir / filename
        
        if filepath.exists():
            # Check if file is valid
            if self._validate_pdf(filepath):
                return {
                    'success': True,
                    'data': {
                        'source': source.name,
                        'filename': filename,
                        'filepath': str(filepath),
                        'size': filepath.stat().st_size,
                        'hash': self._calculate_hash(filepath),
                        'already_downloaded': True
                    }
                }
            else:
                # File is corrupted, re-download
                filepath.unlink()
        
        # Try to download
        for attempt in range(self.max_retries):
            try:
                # Attempt to find PDF URL
                pdf_url = self._find_pdf_url(source)
                
                if not pdf_url:
                    return {
                        'success': False,
                        'error': f"Could not find PDF URL for {source.name}"
                    }
                
                # Download the PDF
                response = requests.get(pdf_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # Save the file
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                # Validate
                if self._validate_pdf(filepath):
                    return {
                        'success': True,
                        'data': {
                            'source': source.name,
                            'filename': filename,
                            'filepath': str(filepath),
                            'size': len(response.content),
                            'hash': self._calculate_hash(filepath),
                            'url': pdf_url,
                            'jurisdiction': source.jurisdiction,
                            'category': source.category,
                            'version': source.version
                        }
                    }
                else:
                    filepath.unlink()
                    return {
                        'success': False,
                        'error': "Downloaded file is not a valid PDF"
                    }
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                return {
                    'success': False,
                    'error': str(e)
                }
        
        return {
            'success': False,
            'error': f"Failed after {self.max_retries} attempts"
        }
    
    def _find_pdf_url(self, source: CodeSource) -> Optional[str]:
        """
        Find the PDF URL for a code source.
        
        Args:
            source: Code source.
            
        Returns:
            URL of the PDF file, or None if not found.
        """
        # Specific URLs for known sources
        known_urls = {
            'FBC Building 2023': 'https://www.floridabuilding.org/fbc/',
            'FBC HVHZ 2023': 'https://www.floridabuilding.org/fbc/',
            'Miami-Dade Amendments 2023': 'https://www.miamidade.gov/building/library/',
            'ASCE 7-22 Wind Loads': 'https://www.asce.org/',
            'CBC Building 2022': 'https://www.dgs.ca.gov/BSC/',
            'CBC Seismic Design': 'https://www.dgs.ca.gov/BSC/',
            'CBC Title 24 Energy': 'https://www.energy.ca.gov/',
            'ASCE 7-22 Seismic Loads': 'https://www.asce.org/',
            'IBC 2021': 'https://www.iccsafe.org/',
            'NFPA 101 2021': 'https://www.nfpa.org/',
        }
        
        base_url = known_urls.get(source.name)
        
        if not base_url:
            # Try to find via search
            return self._search_for_pdf(source)
        
        # Try to find PDF on the page
        try:
            response = requests.get(base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
            
            if pdf_links:
                # Look for the most relevant PDF
                for link in pdf_links:
                    href = link.get('href')
                    if href:
                        # Convert to absolute URL
                        if not href.startswith('http'):
                            href = requests.compat.urljoin(base_url, href)
                        return href
            
            # Some sites use download links
            download_links = soup.find_all('a', href=re.compile(r'download|get|file', re.I))
            for link in download_links:
                href = link.get('href')
                if href and href.endswith('.pdf'):
                    if not href.startswith('http'):
                        href = requests.compat.urljoin(base_url, href)
                    return href
                    
        except Exception as e:
            print(f"  ⚠️ Error finding PDF for {source.name}: {e}")
        
        return None
    
    def _search_for_pdf(self, source: CodeSource) -> Optional[str]:
        """
        Search for a PDF using a search engine.
        
        Args:
            source: Code source.
            
        Returns:
            URL of the PDF file, or None if not found.
        """
        # Simple fallback - construct probable URL
        search_name = source.name.lower().replace(' ', '-')
        return f"https://www.google.com/search?q={search_name}+pdf"
    
    def _generate_filename(self, source: CodeSource) -> str:
        """
        Generate a filename for a code source.
        
        Args:
            source: Code source.
            
        Returns:
            Sanitized filename.
        """
        # Create clean filename
        name = source.name.replace(' ', '_')
        version = source.version.replace(' ', '_')
        jurisdiction = source.jurisdiction.replace(' ', '_')
        
        return f"{jurisdiction}_{name}_{version}.pdf"
    
    def _validate_pdf(self, filepath: Path) -> bool:
        """
        Validate that a file is a valid PDF.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            True if the file is a valid PDF.
        """
        if not filepath.exists() or filepath.stat().st_size < 100:
            return False
        
        try:
            # Try to open with PyMuPDF
            doc = fitz.open(filepath)
            page_count = len(doc)
            doc.close()
            return page_count > 0
        except Exception:
            return False
    
    def _calculate_hash(self, filepath: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            SHA-256 hash as hex string.
        """
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(4096), b''):
                sha256.update(block)
        return sha256.hexdigest()
    
    def get_downloaded_codes(self) -> List[Dict]:
        """Get list of downloaded codes."""
        return self.downloaded_files.get('downloaded', [])
    
    def get_failed_downloads(self) -> List[Dict]:
        """Get list of failed downloads."""
        return self.downloaded_files.get('failed', [])
