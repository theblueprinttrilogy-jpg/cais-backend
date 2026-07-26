#!/usr/bin/env python3
"""
Ingesta desde buildingSMART Data Dictionary (bSDD) API.
Fuente oficial de terminología de construcción.
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

class BSDDIngestor:
    """
    Ingestor de términos desde bSDD API.
    """
    
    def __init__(self):
        self.base_url = "https://identifier.buildingsmart.org/api"
        self.output_dir = Path("src/dashboard/provisional/web/dictionaries")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_standards(self) -> List[Dict]:
        """Obtener estándares disponibles."""
        try:
            response = requests.get(
                f"{self.base_url}/standards",
                headers={"Accept": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('standards', [])
            print(f"⚠️ Error {response.status_code}: {response.text}")
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def get_domains(self, standard_id: str) -> List[Dict]:
        """Obtener dominios de un estándar."""
        try:
            response = requests.get(
                f"{self.base_url}/standards/{standard_id}/domains",
                headers={"Accept": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('domains', [])
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def get_terms(self, standard_id: str, domain_id: str) -> List[Dict]:
        """Obtener términos de un dominio."""
        try:
            response = requests.get(
                f"{self.base_url}/standards/{standard_id}/domains/{domain_id}/terms",
                headers={"Accept": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('terms', [])
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def ingest(self) -> Dict:
        """Ingestar términos desde bSDD."""
        results = {"languages": {}}
        
        print("📥 Conectando a buildingSMART Data Dictionary...")
        
        # Obtener estándares
        standards = self.get_standards()
        print(f"📋 {len(standards)} estándares disponibles")
        
        # Buscar estándares relevantes
        relevant = ['ISO-12006-3', 'OmniClass', 'Uniclass', 'IFD']
        for std in standards:
            std_id = std.get('id', '')
            if any(r.lower() in std_id.lower() for r in relevant):
                print(f"🔍 Procesando: {std_id}")
                domains = self.get_domains(std_id)
                for domain in domains:
                    terms = self.get_terms(std_id, domain.get('id'))
                    print(f"  📄 {domain.get('name')}: {len(terms)} términos")
        
        return results

if __name__ == "__main__":
    ingestor = BSDDIngestor()
    results = ingestor.ingest()
    print("\n✅ Ingesta completada")
