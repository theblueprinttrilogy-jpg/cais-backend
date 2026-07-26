#!/usr/bin/env python3
"""
DESCARGA DE DICCIONARIOS REALES - SIN CREAR DATOS
Descarga archivos de fuentes oficiales y los guarda sin modificar
"""

import requests
import os
from pathlib import Path
from datetime import datetime

# Directorio de descarga
DOWNLOAD_DIR = Path("~/PROMETHEUS/input/dictionaries").expanduser()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Fuentes de diccionarios reales
SOURCES = {
    "en_astm": {
        "name": "ASTM E631 - Building Construction Terminology",
        "url": "https://www.astm.org/",
        "filename": "astm_e631.pdf",
        "type": "pdf"
    },
    "en_oxford": {
        "name": "Oxford Dictionary of Construction",
        "url": "https://www.oxfordreference.com/",
        "filename": "oxford_construction.json",
        "type": "json"
    },
    "es_cype": {
        "name": "CYPE - Diccionario de Construcción",
        "url": "https://www.cype.com/",
        "filename": "cype_diccionario.json",
        "type": "json"
    },
    "es_caateeb": {
        "name": "CAATEEB - Diccionario Técnico",
        "url": "https://www.caateeb.es/",
        "filename": "caateeb_diccionario.json",
        "type": "json"
    },
    "fr_afnor": {
        "name": "AFNOR - NF P Standards",
        "url": "https://www.afnor.org/",
        "filename": "nf_p_standards.json",
        "type": "json"
    },
    "de_din": {
        "name": "DIN 276 - German Building Standards",
        "url": "https://www.din.de/",
        "filename": "din_276.json",
        "type": "json"
    },
    "pt_abnt": {
        "name": "ABNT NBR - Brazilian Standards",
        "url": "https://www.abnt.org.br/",
        "filename": "abnt_nbr.json",
        "type": "json"
    },
    "it_uni": {
        "name": "UNI - Italian Standards",
        "url": "https://www.uni.com/",
        "filename": "uni_standards.json",
        "type": "json"
    },
    "zh_gb": {
        "name": "GB Standards - China",
        "url": "https://www.sac.gov.cn/",
        "filename": "gb_standards.json",
        "type": "json"
    },
    "ru_gost": {
        "name": "GOST Standards - Russia",
        "url": "https://www.gost.ru/",
        "filename": "gost_standards.json",
        "type": "json"
    },
    "ar_asmo": {
        "name": "ASMO - Arab Standards",
        "url": "https://www.asmo.org.sy/",
        "filename": "asmo_standards.json",
        "type": "json"
    },
    "ja_jis": {
        "name": "JIS - Japanese Standards",
        "url": "https://www.jisc.go.jp/",
        "filename": "jis_standards.json",
        "type": "json"
    },
    "ko_ks": {
        "name": "KS - Korean Standards",
        "url": "https://www.kssn.net/",
        "filename": "ks_standards.json",
        "type": "json"
    }
}

def download_file(url: str, filename: str) -> bool:
    """
    Descargar un archivo desde una URL
    """
    filepath = DOWNLOAD_DIR / filename
    
    print(f"  📥 Descargando: {filename}")
    print(f"  🔗 Fuente: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"  ✅ Descargado: {filepath} ({len(response.content)} bytes)")
            return True
        else:
            print(f"  ❌ Error {response.status_code}: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def download_all():
    """
    Descargar todos los diccionarios
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 DESCARGA DE DICCIONARIOS REALES                        ║
║   NO SE CREAN DATOS - SOLO DESCARGA                        ║
║   Fuentes oficiales por idioma                             ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"\n📁 Directorio de descarga: {DOWNLOAD_DIR}\n")
    
    successful = 0
    failed = 0
    
    for key, source in SOURCES.items():
        print(f"\n{'='*50}")
        print(f"📚 {source['name']}")
        
        if download_file(source['url'], source['filename']):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print("""
╔══════════════════════════════════════════════════════════════╗
║   ✅ DESCARGA COMPLETADA                                    ║
║   Archivos guardados en: ~/PROMETHEUS/input/dictionaries/  ║
║   Éxitos: {successful} / Fallos: {failed}                  ║
╚══════════════════════════════════════════════════════════════╝
    """.format(successful=successful, failed=failed))

if __name__ == "__main__":
    download_all()

