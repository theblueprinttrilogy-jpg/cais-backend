#!/usr/bin/env python3
"""
Zoning Data Downloader V2 - Usando fuentes REALES accesibles
"""

import os
import json
import requests
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import zipfile
import io


class ZoningDownloaderV2:
    """
    Descarga datos de zonificación REALES desde fuentes accesibles
    """

    def __init__(self, data_dir: str = "~/PROMETHEUS/data/zoning"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Fuentes REALES y accesibles
        self.sources = {
            "miami_zoning": {
                "name": "Miami-Dade Zoning",
                "url": "https://opendata.miamidade.gov/api/v2/catalog/datasets/zoning-districts/exports/json",
                "type": "json"
            },
            "miami_land_use": {
                "name": "Miami-Dade Land Use",
                "url": "https://opendata.miamidade.gov/api/v2/catalog/datasets/land-use-2015/exports/json",
                "type": "json"
            },
            "florida_zoning": {
                "name": "Florida Zoning Data",
                "url": "https://www.floridagis.com/data/zoning.json",
                "type": "json"
            },
            "us_zoning": {
                "name": "US Zoning Data",
                "url": "https://datausa.io/api/data",
                "type": "json"
            }
        }

        print(f"📂 Zoning data directory: {self.data_dir}")

    def download_miami_zoning(self) -> Optional[Dict]:
        """
        Descargar datos de zonificación de Miami-Dade Open Data Portal
        """
        print("\n📥 Downloading Miami-Dade zoning data from Open Data Portal...")

        try:
            url = "https://opendata.miamidade.gov/api/v2/catalog/datasets/zoning-districts/exports/json"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Downloaded {len(data)} zoning records from Miami-Dade")
                
                # Save raw data
                filepath = self.data_dir / "miami_zoning_raw.json"
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved to {filepath}")
                
                return data
            else:
                print(f"❌ Error {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def download_miami_land_use(self) -> Optional[Dict]:
        """
        Descargar datos de uso de suelo de Miami-Dade
        """
        print("\n📥 Downloading Miami-Dade land use data...")

        try:
            url = "https://opendata.miamidade.gov/api/v2/catalog/datasets/land-use-2015/exports/json"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Downloaded {len(data)} land use records")
                
                filepath = self.data_dir / "miami_land_use.json"
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved to {filepath}")
                
                return data
            else:
                print(f"❌ Error {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def download_florida_gis(self) -> Optional[Dict]:
        """
        Descargar datos de zonificación de Florida GIS
        """
        print("\n📥 Downloading Florida GIS zoning data...")

        try:
            # Florida GIS Open Data
            url = "https://www.floridagis.com/data/zoning.geojson"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get("features", [])
                print(f"✅ Downloaded {len(records)} zoning features from Florida GIS")
                
                filepath = self.data_dir / "florida_zoning.geojson"
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved to {filepath}")
                
                return data
            else:
                print(f"❌ Error {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def download_zoning_by_city(self, city: str = "Miami") -> Dict:
        """
        Buscar y descargar zonificación para una ciudad específica
        """
        print(f"\n📥 Searching zoning data for {city}...")

        results = {
            "city": city,
            "timestamp": datetime.now().isoformat(),
            "sources": {}
        }

        # 1. Intentar desde Open Data Portal
        if city.lower() == "miami":
            data = self.download_miami_zoning()
            if data:
                results["sources"]["miami_opendata"] = len(data)

            land_use = self.download_miami_land_use()
            if land_use:
                results["sources"]["miami_land_use"] = len(land_use)

        # 2. Intentar Florida GIS
        fl_data = self.download_florida_gis()
        if fl_data:
            results["sources"]["florida_gis"] = len(fl_data.get("features", []))

        # 3. Guardar resultados
        self._save_results(results)

        return results

    def _save_results(self, results: Dict):
        """Guardar resultados"""
        filepath = self.data_dir / "zoning_download_results.json"
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {filepath}")

    def download_all(self) -> Dict:
        """
        Descargar todas las fuentes disponibles
        """
        print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 REAL ZONING DATA DOWNLOADER V2                         ║
║   Fuentes: Miami-Dade Open Data, Florida GIS               ║
╚══════════════════════════════════════════════════════════════╝
        """)

        results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "total_records": 0
        }

        # Miami zoning
        miami = self.download_zoning_by_city("Miami")
        results["sources"]["miami"] = miami["sources"]
        results["total_records"] += sum(miami["sources"].values())

        # Guardar
        self._save_results(results)

        print(f"\n✅ Total records downloaded: {results['total_records']}")
        return results


def main():
    downloader = ZoningDownloaderV2()
    results = downloader.download_all()


if __name__ == "__main__":
    main()
