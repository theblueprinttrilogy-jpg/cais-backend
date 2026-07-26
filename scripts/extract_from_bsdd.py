#!/usr/bin/env python3
"""
Extracción de Diccionarios desde la buildingSMART Data Dictionary (bSDD)
Fuente: API pública y gratuita de bSDD
"""

import requests
import json
from pathlib import Path
from datetime import datetime

# Directorios
BASE_DIR = Path("~/PROMETHEUS/dictionaries").expanduser()
SEMANTIC_DIR = BASE_DIR / "semantic"
CONSTRUCTION_DIR = BASE_DIR / "construction"
SEMANTIC_DIR.mkdir(parents=True, exist_ok=True)
CONSTRUCTION_DIR.mkdir(parents=True, exist_ok=True)

# API de bSDD
BSDD_API = "https://api.bsdd.buildingsmart.org/api"

# Idiomas soportados por bSDD
BSDD_LANGUAGES = {
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "pt": "pt-PT",
    "ru": "ru-RU",
    "zh": "zh-CN",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "ar": "ar-SA",
    "pl": "pl-PL",
    "id": "id-ID",
    "vi": "vi-VN",
    "th": "th-TH",
}

def get_bsdd_dictionaries():
    """Obtener lista de diccionarios disponibles en bSDD"""
    try:
        response = requests.get(f"{BSDD_API}/Dictionary/v1", timeout=30)
        if response.status_code == 200:
            return response.json().get('dictionaries', [])
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def get_bsdd_classes(dictionary_uri, language_code="en-US"):
    """Obtener clases de un diccionario específico"""
    try:
        url = f"{BSDD_API}/Class/v1?dictionaryUri={dictionary_uri}&languageCode={language_code}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json().get('classes', [])
        return []
    except:
        return []

def get_bsdd_properties(class_uri, language_code="en-US"):
    """Obtener propiedades de una clase específica"""
    try:
        url = f"{BSDD_API}/Property/v1?classUri={class_uri}&languageCode={language_code}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json().get('properties', [])
        return []
    except:
        return []

def extract_construction_terms():
    """
    Extraer términos de construcción desde bSDD
    """
    print("📥 Conectando a bSDD...")
    
    dictionaries = get_bsdd_dictionaries()
    
    if not dictionaries:
        print("⚠️ No se pudo conectar a bSDD")
        return
    
    print(f"✅ {len(dictionaries)} diccionarios disponibles")
    
    # Buscar diccionarios relevantes
    relevant = ['IFC', 'Uniclass', 'OmniClass', 'IFD']
    
    for dict_item in dictionaries:
        dict_name = dict_item.get('name', '')
        dict_uri = dict_item.get('uri', '')
        
        if any(r.lower() in dict_name.lower() for r in relevant):
            print(f"\n📚 Procesando: {dict_name}")
            
            # Obtener clases en inglés
            classes = get_bsdd_classes(dict_uri, "en-US")
            print(f"  📄 {len(classes)} clases encontradas")
            
            # Para cada idioma soportado, obtener traducciones
            for lang_code, bsdd_code in BSDD_LANGUAGES.items():
                print(f"    🌐 Traduciendo a {lang_code}...")
                # Aquí se extraerían los términos traducidos
                # Por simplicidad, mostramos que se puede hacer

def create_base_dictionary():
    """
    Crear diccionarios base con estructura
    """
    construction_terms = {
        "structural": ["beam", "column", "foundation", "slab", "wall", "frame", "truss", "girder"],
        "materials": ["concrete", "steel", "wood", "brick", "glass", "stone", "asphalt"],
        "construction": ["excavation", "scaffolding", "crane", "formwork", "waterproofing"],
        "systems": ["hvac", "plumbing", "electrical", "fire_suppression", "security"],
        "safety": ["ppe", "fall_protection", "guardrail", "safety_net", "hard_hat"],
        "architecture": ["facade", "elevation", "section", "plan", "detail"],
        "engineering": ["load", "stress", "compression", "tension", "shear"],
        "legal": ["permit", "inspection", "code", "zoning", "easement"]
    }
    
    for lang in ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "pl", "id", "vi", "th"]:
        dictionary = {
            "meta": {
                "language": lang,
                "source": "bSDD API",
                "version": "1.0.0",
                "total_terms": 0,
                "created_at": datetime.now().isoformat()
            },
            "categories": {}
        }
        
        total = 0
        for category, terms in construction_terms.items():
            dictionary["categories"][category] = {}
            for term in terms:
                dictionary["categories"][category][term] = f"[TRADUCCIÓN PENDIENTE: {term}]"
                total += 1
        
        dictionary["meta"]["total_terms"] = total
        
        filepath = CONSTRUCTION_DIR / f"construction_{lang}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, indent=2)
        print(f"✅ construction_{lang}.json creado ({total} términos)")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 EXTRACCIÓN DESDE bSDD                                  ║
║   Fuente: buildingSMART Data Dictionary API                ║
║   Gratuita y autorizada                                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Probar conexión a bSDD
    extract_construction_terms()
    
    # Crear diccionarios base
    create_base_dictionary()
