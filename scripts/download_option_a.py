#!/usr/bin/env python3
"""
DESCARGA OPCIÓN A - Diccionarios desde fuentes existentes
1. Diccionarios semánticos: OpenMultilingualWordNet + MUSE
2. Diccionarios de construcción: Fuentes oficiales
"""

import requests
import json
import csv
import os
from pathlib import Path
from datetime import datetime
import zipfile
import io

# Directorios
BASE_DIR = Path("~/PROMETHEUS/dictionaries").expanduser()
SEMANTIC_DIR = BASE_DIR / "semantic"
CONSTRUCTION_DIR = BASE_DIR / "construction"
SEMANTIC_DIR.mkdir(parents=True, exist_ok=True)
CONSTRUCTION_DIR.mkdir(parents=True, exist_ok=True)

# 20 idiomas
LANGUAGES = {
    "en": "English",
    "es": "Español",
    "zh": "中文",
    "hi": "हिन्दी",
    "ar": "العربية",
    "fr": "Français",
    "pt": "Português",
    "ru": "Русский",
    "ur": "اردو",
    "id": "Bahasa Indonesia",
    "de": "Deutsch",
    "ja": "日本語",
    "sw": "Kiswahili",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "vi": "Tiếng Việt",
    "ko": "한국어",
    "it": "Italiano",
    "th": "ภาษาไทย",
    "pl": "Polski"
}

# Idiomas excluidos para semánticos (inglés no necesita traducción)
SEMANTIC_LANGUAGES = [lang for lang in LANGUAGES.keys() if lang != "en"]

def download_open_multilingual_wordnet():
    """
    Descargar OpenMultilingualWordNet (OMW)
    https://github.com/globalwordnet/omw
    """
    print("\n📥 Descargando OpenMultilingualWordNet...")
    
    # OMW está disponible en GitHub
    url = "https://raw.githubusercontent.com/globalwordnet/omw/refs/heads/main/omw.json"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            # Guardar el archivo completo
            filepath = SEMANTIC_DIR / "omw_full.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"  ✅ OMW descargado: {filepath}")
            
            # Extraer solo los idiomas necesarios
            for lang in SEMANTIC_LANGUAGES:
                extracted = extract_omw_language(data, lang)
                if extracted:
                    lang_file = SEMANTIC_DIR / f"en_to_{lang}.json"
                    with open(lang_file, 'w', encoding='utf-8') as f:
                        json.dump(extracted, f, indent=2)
                    print(f"  ✅ en_to_{lang}.json creado")
            
            return True
        else:
            print(f"  ❌ Error {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def extract_omw_language(omw_data, lang_code):
    """
    Extraer datos de un idioma específico desde OMW
    """
    try:
        # Buscar el idioma en los datos de OMW
        if "languages" in omw_data and lang_code in omw_data["languages"]:
            lang_data = omw_data["languages"][lang_code]
            return lang_data
        return None
    except:
        return None

def download_muse():
    """
    Descargar MUSE (Facebook) - Embeddings multilingües
    https://github.com/facebookresearch/MUSE
    """
    print("\n📥 Descargando MUSE...")
    
    # MUSE está disponible en GitHub
    base_url = "https://raw.githubusercontent.com/facebookresearch/MUSE/main/embeddings/"
    
    # Idiomas disponibles en MUSE
    muse_languages = ["es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar"]
    
    for lang in muse_languages:
        url = f"{base_url}en_{lang}.txt"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                filepath = SEMANTIC_DIR / f"muse_en_{lang}.txt"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  ✅ muse_en_{lang}.txt descargado")
            else:
                print(f"  ⚠️ muse_en_{lang}.txt no disponible")
        except Exception as e:
            print(f"  ⚠️ {lang}: {e}")

def download_construction_astm():
    """
    Descargar ASTM E631 - Construcción en inglés
    """
    print("\n📥 Descargando ASTM E631...")
    
    # Intentar desde varias fuentes
    urls = [
        "https://www.astm.org/",
        "https://www.astm.org/astm_e631.pdf",
        "https://standards.astm.org/astm_e631.pdf"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200 and len(response.content) > 10000:
                filepath = CONSTRUCTION_DIR / "construction_en.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  ✅ ASTM E631 descargado: {filepath}")
                return True
        except:
            continue
    
    print("  ⚠️ ASTM E631 no disponible. Se usará corpus base.")
    return False

def create_construction_dictionary(lang_code, base_terms):
    """
    Crear diccionario de construcción para un idioma
    """
    dictionary = {
        "meta": {
            "language": lang_code,
            "name": LANGUAGES.get(lang_code, lang_code),
            "source": "ASTM E631 + Traducción semántica",
            "version": "1.0.0",
            "total_terms": 0,
            "created_at": datetime.now().isoformat()
        },
        "categories": {}
    }
    
    total_terms = 0
    categories = ["structural", "materials", "construction", "systems", "safety", "architecture", "engineering", "legal"]
    
    for category in categories:
        dictionary["categories"][category] = {}
        for term in base_terms.get(category, []):
            # Traducción placeholder (se reemplazará con datos reales)
            dictionary["categories"][category][term] = f"[TRADUCCIÓN: {term}]"
            total_terms += 1
    
    dictionary["meta"]["total_terms"] = total_terms
    return dictionary

def create_construction_dictionaries():
    """
    Crear diccionarios de construcción para todos los idiomas
    """
    print("\n📥 Creando diccionarios de construcción...")
    
    # Base de términos de construcción
    base_terms = {
        "structural": ["beam", "column", "foundation", "slab", "wall", "frame", "truss", "girder"],
        "materials": ["concrete", "steel", "wood", "brick", "glass", "stone", "asphalt"],
        "construction": ["excavation", "scaffolding", "crane", "formwork", "waterproofing"],
        "systems": ["hvac", "plumbing", "electrical", "fire_suppression", "security"],
        "safety": ["ppe", "fall_protection", "guardrail", "safety_net", "hard_hat"],
        "architecture": ["facade", "elevation", "section", "plan", "detail"],
        "engineering": ["load", "stress", "compression", "tension", "shear"],
        "legal": ["permit", "inspection", "code", "zoning", "easement"]
    }
    
    for lang in LANGUAGES.keys():
        dictionary = create_construction_dictionary(lang, base_terms)
        filepath = CONSTRUCTION_DIR / f"construction_{lang}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, indent=2)
        print(f"  ✅ construction_{lang}.json creado")

def download_all():
    """
    Ejecutar todas las descargas
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 OPCIÓN A - DESCARGA DESDE FUENTES EXISTENTES          ║
║   1. OpenMultilingualWordNet (OMW)                         ║
║   2. MUSE (Facebook)                                       ║
║   3. Diccionarios de Construcción                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Descargar OMW
    omw_success = download_open_multilingual_wordnet()
    
    # 2. Descargar MUSE
    muse_success = download_muse()
    
    # 3. Descargar ASTM E631
    astm_success = download_construction_astm()
    
    # 4. Crear diccionarios de construcción
    create_construction_dictionaries()
    
    # Resumen
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   ✅ DESCARGA COMPLETADA                                    ║
║   OMW: {'✅ OK' if omw_success else '⚠️ No disponible'}                      ║
║   MUSE: {'✅ OK' if muse_success else '⚠️ No disponible'}                     ║
║   ASTM: {'✅ OK' if astm_success else '⚠️ No disponible'}                     ║
║   Diccionarios de construcción: ✅ Creados                  ║
║                                                             ║
║   📁 Semánticos: {SEMANTIC_DIR}                          ║
║   📁 Construcción: {CONSTRUCTION_DIR}                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    download_all()
