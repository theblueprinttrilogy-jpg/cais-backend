#!/usr/bin/env python3
"""
Smart Code Aggregator - Busca e ingiere códigos normativos de múltiples fuentes
"""

import os
import re
import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import time

logger = logging.getLogger(__name__)

class SmartCodeAggregator:
    """
    Busca, descarga e ingiere códigos normativos automáticamente.
    """
    
    def __init__(self, output_dir: Path = Path("~/PROMETHEUS/input/codes")):
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.search_queries = [
            "international building code pdf",
            "ibc 2021 pdf free",
            "building code pdf download",
            "construction codes regulations pdf",
            "building standards code pdf",
            "code compliance building regulations pdf",
            "international building code 2021 free download"
        ]
        
        self.downloaded_files = []
        self.failed_downloads = []
        
        logger.info(f"SmartCodeAggregator initialized. Output: {self.output_dir}")
    
    def aggregate_codes(self) -> Dict[str, Any]:
        """
        Busca y descarga códigos normativos.
        """
        results = {
            'downloaded': [],
            'failed': [],
            'found': [],
            'total': 0
        }
        
        print("🔍 Buscando códigos normativos...")
        
        # Buscar en fuentes conocidas
        code_sources = self._get_code_sources()
        
        for source in code_sources:
            print(f"  📄 Buscando: {source['name']}")
            
            # Intentar URL principal
            success = self._try_download_source(source)
            
            if success:
                results['downloaded'].append(source['name'])
                results['total'] += 1
            else:
                results['failed'].append(source['name'])
            
            time.sleep(1)  # Evitar rate limiting
        
        # Guardar resultados
        self._save_results(results)
        
        return results
    
    def _get_code_sources(self) -> List[Dict]:
        """Obtiene fuentes de códigos normativos"""
        return [
            {
                'name': 'IBC 2021',
                'url': 'https://codes.iccsafe.org/content/IBC2021P1',
                'type': 'web'
            },
            {
                'name': 'International Building Code',
                'url': 'https://www.iccsafe.org/codes-tech-support/codes/2021-international-building-code/',
                'type': 'web'
            },
            {
                'name': 'Florida Building Code',
                'url': 'https://www.floridabuilding.org/',
                'type': 'web'
            },
            {
                'name': 'California Building Code',
                'url': 'https://www.dgs.ca.gov/BSC/Codes',
                'type': 'web'
            },
            {
                'name': 'NFPA Codes',
                'url': 'https://www.nfpa.org/codes-and-standards/all-codes-and-standards/list-of-codes-and-standards',
                'type': 'web'
            },
            {
                'name': 'OSHA Regulations',
                'url': 'https://www.osha.gov/laws-regs/regulations/standardnumber',
                'type': 'web'
            }
        ]
    
    def _try_download_source(self, source: Dict) -> bool:
        """Intenta descargar de una fuente"""
        try:
            # Intentar con requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(
                source['url'],
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Guardar contenido HTML
                filename = f"{source['name'].replace(' ', '_')}.html"
                file_path = self.output_dir / filename
                file_path.write_text(response.text, encoding='utf-8')
                
                # Buscar enlaces a PDF en la página
                pdf_links = self._find_pdf_links(response.text)
                
                if pdf_links:
                    print(f"    ✅ Encontrados {len(pdf_links)} PDFs en {source['name']}")
                    for link in pdf_links[:2]:  # Descargar hasta 2 PDFs
                        self._download_pdf(link, source['name'])
                else:
                    print(f"    ⚠️ No se encontraron PDFs en {source['name']}")
                
                return True
            else:
                print(f"    ❌ Error {response.status_code}: {source['name']}")
                return False
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            return False
    
    def _find_pdf_links(self, html: str) -> List[str]:
        """Encuentra enlaces a PDF en HTML"""
        import re
        pdf_patterns = [
            r'href="([^"]*\.pdf[^"]*)"',
            r'href="([^"]*\.pdf[^"]*)"',
            r'src="([^"]*\.pdf[^"]*)"',
            r'link="([^"]*\.pdf[^"]*)"'
        ]
        
        links = []
        for pattern in pdf_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            links.extend(matches)
        
        # Limpiar y filtrar
        links = [link for link in links if not link.startswith('#')]
        
        # Completar URLs relativas
        base_url = "https://codes.iccsafe.org/"
        links = [link if link.startswith('http') else base_url + link for link in links]
        
        return list(set(links))  # Eliminar duplicados
    
    def _download_pdf(self, url: str, source_name: str):
        """Descarga un PDF"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
                filename = f"{source_name.replace(' ', '_')}_{int(time.time())}.pdf"
                file_path = self.output_dir / filename
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"      ✅ Descargado: {filename} ({file_path.stat().st_size // 1024} KB)")
                self.downloaded_files.append(str(file_path))
                return True
                
        except Exception as e:
            print(f"      ❌ Error descargando: {e}")
            self.failed_downloads.append(url)
        
        return False
    
    def _save_results(self, results: Dict):
        """Guarda los resultados de la agregación"""
        results_path = self.output_dir / "aggregation_results.json"
        
        results_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'downloaded_files': self.downloaded_files,
            'failed_downloads': self.failed_downloads,
            'total_downloaded': len(self.downloaded_files)
        }
        
        with open(results_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n✅ Resultados guardados en: {results_path}")


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🔍 SMART CODE AGGREGATOR - CAIS AUTOPOIETIC         ║
║                                                           ║
║     Buscando códigos normativos...                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    aggregator = SmartCodeAggregator()
    results = aggregator.aggregate_codes()
    
    print("\n" + "="*60)
    print("📊 AGREGACIÓN COMPLETA")
    print("="*60)
    print(f"   Descargados: {len(results['downloaded'])} códigos")
    print(f"   Fallidos: {len(results['failed'])} códigos")
    print(f"   Total encontrados: {results['total']}")
    print("="*60)
    print(f"\n📁 Output: {aggregator.output_dir}")
