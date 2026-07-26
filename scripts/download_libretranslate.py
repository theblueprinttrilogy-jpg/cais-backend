#!/usr/bin/env python3
"""
DESCARGA USANDO LIBRETRANSLATE
Alternativa gratuita sin API key
"""

import requests
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("~/PROMETHEUS/dictionaries").expanduser()
SEMANTIC_DIR = BASE_DIR / "semantic"
SEMANTIC_DIR.mkdir(parents=True, exist_ok=True)

# 19 idiomas objetivo (todos menos inglés)
LANGUAGES = {
    "es": "Español",
    "zh": "Chinese",
    "hi": "Hindi",
    "ar": "Arabic",
    "fr": "French",
    "pt": "Portuguese",
    "ru": "Russian",
    "ur": "Urdu",
    "id": "Indonesian",
    "de": "German",
    "ja": "Japanese",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "vi": "Vietnamese",
    "ko": "Korean",
    "it": "Italian",
    "th": "Thai",
    "pl": "Polish"
}

# Palabras de construcción a traducir
CONSTRUCTION_TERMS = [
    "beam", "column", "foundation", "slab", "wall", "frame", "truss", "girder",
    "concrete", "steel", "wood", "brick", "glass", "stone", "asphalt",
    "excavation", "scaffolding", "crane", "formwork", "waterproofing",
    "hvac", "plumbing", "electrical", "fire_suppression", "security",
    "ppe", "fall_protection", "guardrail", "safety_net", "hard_hat",
    "facade", "elevation", "section", "plan", "detail",
    "load", "stress", "compression", "tension", "shear",
    "permit", "inspection", "code", "zoning", "easement"
]

def translate_with_libretranslate(text, target_lang, source_lang="en"):
    """
    Traducir usando LibreTranslate API
    """
    url = "https://libretranslate.com/translate"
    
    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("translatedText", text)
        else:
            return text
    except:
        return text

def create_semantic_dictionary(target_lang):
    """
    Crear diccionario semántico traduciendo términos de construcción
    """
    dictionary = {
        "meta": {
            "source_language": "en",
            "target_language": target_lang,
            "language_name": LANGUAGES.get(target_lang, target_lang),
            "total_terms": 0,
            "created_at": datetime.now().isoformat()
        },
        "translations": {}
    }
    
    print(f"  🌐 Traduciendo al {LANGUAGES.get(target_lang, target_lang)}...")
    
    for term in CONSTRUCTION_TERMS:
        translated = translate_with_libretranslate(term, target_lang)
        dictionary["translations"][term] = translated
    
    dictionary["meta"]["total_terms"] = len(CONSTRUCTION_TERMS)
    return dictionary

def download_all():
    print("""
╔══════════════════════════════════════════════════════════════╗
║   📥 DESCARGA CON LIBRETRANSLATE                            ║
║   Alternativa gratuita sin API key                         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    for lang_code in LANGUAGES.keys():
        dictionary = create_semantic_dictionary(lang_code)
        filepath = SEMANTIC_DIR / f"en_to_{lang_code}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, indent=2)
        print(f"  ✅ en_to_{lang_code}.json creado ({dictionary['meta']['total_terms']} términos)")
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   ✅ DESCARGA COMPLETADA                                    ║
║   {len(LANGUAGES)} diccionarios semánticos creados                     ║
║   📁 {SEMANTIC_DIR}                                         ║
╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    download_all()
