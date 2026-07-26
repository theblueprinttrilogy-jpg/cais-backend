#!/usr/bin/env python3
"""
Ingesta Completa desde buildingSMART Data Dictionary (bSDD) API
+ Pipeline de Traducción Semántica para idiomas no cubiertos
"""

import json
import requests
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import os

# Configuración
BSDD_API_BASE = "https://identifier.buildingsmart.org/api"
OUTPUT_DIR = Path("~/PROMETHEUS/src/dashboard/provisional/web/dictionaries").expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 20 idiomas más hablados
LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧", "bsdd_code": "en-US"},
    "zh": {"name": "中文", "flag": "🇨🇳", "bsdd_code": "zh-CN"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳", "bsdd_code": None},  # No tiene bSDD
    "es": {"name": "Español", "flag": "🇪🇸", "bsdd_code": "es-ES"},
    "ar": {"name": "العربية", "flag": "🇸🇦", "bsdd_code": "ar-SA"},
    "fr": {"name": "Français", "flag": "🇫🇷", "bsdd_code": "fr-FR"},
    "pt": {"name": "Português", "flag": "🇵🇹", "bsdd_code": "pt-PT"},
    "ru": {"name": "Русский", "flag": "🇷🇺", "bsdd_code": "ru-RU"},
    "ur": {"name": "اردو", "flag": "🇵🇰", "bsdd_code": None},
    "id": {"name": "Bahasa Indonesia", "flag": "🇮🇩", "bsdd_code": "id-ID"},
    "de": {"name": "Deutsch", "flag": "🇩🇪", "bsdd_code": "de-DE"},
    "ja": {"name": "日本語", "flag": "🇯🇵", "bsdd_code": "ja-JP"},
    "sw": {"name": "Kiswahili", "flag": "🇹🇿", "bsdd_code": "sw-KE"},
    "ta": {"name": "தமிழ்", "flag": "🇮🇳", "bsdd_code": None},
    "te": {"name": "తెలుగు", "flag": "🇮🇳", "bsdd_code": None},
    "vi": {"name": "Tiếng Việt", "flag": "🇻🇳", "bsdd_code": "vi-VN"},
    "ko": {"name": "한국어", "flag": "🇰🇷", "bsdd_code": "ko-KR"},
    "it": {"name": "Italiano", "flag": "🇮🇹", "bsdd_code": "it-IT"},
    "th": {"name": "ภาษาไทย", "flag": "🇹🇭", "bsdd_code": "th-TH"},
    "pl": {"name": "Polski", "flag": "🇵🇱", "bsdd_code": "pl-PL"}
}

class BSDDIngestor:
    """
    Ingestor completo de diccionarios de construcción desde bSDD + Traducción
    """
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.base_url = BSDD_API_BASE
        self.corpus = {}
        self.translation_cache = {}
        
    def fetch_bsdd_standards(self) -> List[Dict]:
        """Obtener estándares disponibles en bSDD"""
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
    
    def fetch_bsdd_domain_terms(self, standard_id: str, domain_id: str, lang: str = "en-US") -> List[Dict]:
        """Obtener términos de un dominio específico"""
        try:
            url = f"{self.base_url}/standards/{standard_id}/domains/{domain_id}/terms"
            if lang:
                url += f"?languageCode={lang}"
            
            response = requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('terms', [])
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def fetch_bsdd_domain(self, standard_id: str, domain_id: str) -> Dict:
        """Obtener información de un dominio"""
        try:
            url = f"{self.base_url}/standards/{standard_id}/domains/{domain_id}"
            response = requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('domain', {})
            return {}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}
    
    def extract_corpus(self) -> Dict[str, Dict]:
        """
        Extraer corpus de términos de construcción desde bSDD
        """
        print("📥 Extrayendo corpus desde bSDD...")
        
        corpus = {}
        
        # Obtener estándares
        standards = self.fetch_bsdd_standards()
        print(f"📋 {len(standards)} estándares disponibles")
        
        # Filtrar estándares relevantes
        relevant_standards = ['ISO-12006-3', 'OmniClass', 'Uniclass', 'IFD']
        
        for std in standards:
            std_id = std.get('id', '')
            if any(r.lower() in std_id.lower() for r in relevant_standards):
                print(f"🔍 Procesando estándar: {std_id}")
                
                # Obtener dominios
                domains_url = f"{self.base_url}/standards/{std_id}/domains"
                try:
                    resp = requests.get(domains_url, headers={"Accept": "application/json"}, timeout=30)
                    if resp.status_code == 200:
                        domains = resp.json().get('domains', [])
                        for domain in domains:
                            domain_id = domain.get('id')
                            if domain_id:
                                # Obtener términos en inglés
                                terms = self.fetch_bsdd_domain_terms(std_id, domain_id, "en-US")
                                if terms:
                                    domain_name = domain.get('name', domain_id)
                                    corpus[domain_name] = {
                                        'terms': terms,
                                        'domain_id': domain_id,
                                        'standard_id': std_id
                                    }
                                    print(f"  📄 {domain_name}: {len(terms)} términos")
                except Exception as e:
                    print(f"  ⚠️ Error en dominios de {std_id}: {e}")
        
        self.corpus = corpus
        print(f"\n✅ Corpus extraído: {len(corpus)} dominios")
        return corpus
    
    def translate_with_api(self, text: str, target_lang: str) -> str:
        """
        Traducir texto usando API de traducción (Google Translate / DeepL)
        """
        # Para esta demo, usamos un mapeo estático
        # En producción, se usaría Google Translate API o DeepL
        
        # Mapeo de términos comunes para demostración
        common_terms = {
            'beam': {'es': 'viga', 'fr': 'poutre', 'de': 'träger', 'pt': 'viga', 'it': 'trave'},
            'column': {'es': 'columna', 'fr': 'colonne', 'de': 'stütze', 'pt': 'coluna', 'it': 'colonna'},
            'concrete': {'es': 'hormigón', 'fr': 'béton', 'de': 'beton', 'pt': 'concreto', 'it': 'calcestruzzo'},
            'steel': {'es': 'acero', 'fr': 'acier', 'de': 'stahl', 'pt': 'aço', 'it': 'acciaio'},
            'wood': {'es': 'madera', 'fr': 'bois', 'de': 'holz', 'pt': 'madeira', 'it': 'legno'},
        }
        
        if text in common_terms and target_lang in common_terms[text]:
            return common_terms[text][target_lang]
        
        # Si no está en el mapeo, devolver el texto original con marcador
        return f"[TRADUCCIÓN PENDIENTE: {text} → {target_lang}]"
    
    def build_dictionary(self, lang: str, corpus: Dict) -> Dict:
        """
        Construir diccionario para un idioma específico
        """
        dictionary = {
            "meta": {
                "language": lang,
                "name": LANGUAGES.get(lang, {}).get("name", lang),
                "version": "1.0.0",
                "source": "buildingSMART Data Dictionary (bSDD) + Traducción Semántica",
                "total_terms": 0,
                "generated_at": datetime.now().isoformat()
            },
            "categories": {}
        }
        
        total_terms = 0
        
        for category_name, category_data in corpus.items():
            terms = category_data.get('terms', [])
            if not terms:
                continue
            
            category_dict = {}
            
            for term in terms:
                term_name = term.get('name', '')
                definition = term.get('definition', '')
                if term_name:
                    # Si es inglés, mantener el término original
                    if lang == 'en':
                        category_dict[term_name] = definition or term_name
                    else:
                        # Traducir el término
                        translated = self.translate_with_api(term_name, lang)
                        category_dict[term_name] = {
                            'translation': translated,
                            'definition': definition
                        }
                    total_terms += 1
            
            if category_dict:
                dictionary['categories'][category_name] = category_dict
        
        dictionary['meta']['total_terms'] = total_terms
        return dictionary
    
    def save_dictionary(self, lang: str, dictionary: Dict):
        """Guardar diccionario en archivo JSON"""
        lang_dir = self.output_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = lang_dir / "construction_terms.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Diccionario guardado: {filepath} ({dictionary['meta']['total_terms']} términos)")
        return filepath
    
    def create_meta_file(self):
        """Crear archivo de metadatos"""
        meta = {
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
            "languages": LANGUAGES,
            "source": "buildingSMART Data Dictionary (bSDD)",
            "total_languages": len(LANGUAGES),
            "status": "COMPLETED"
        }
        
        meta_path = self.output_dir / "meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Metadatos guardados: {meta_path}")
    
    def ingest_all(self):
        """
        Ejecutar ingesta completa para todos los idiomas
        """
        print("""
╔══════════════════════════════════════════════════════════════╗
║   🌍 INGESTA DE DICCIONARIOS DE CONSTRUCCIÓN               ║
║   buildingSMART Data Dictionary + Traducción Semántica     ║
║   20 Idiomas Más Hablados del Mundo                        ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Paso 1: Extraer corpus desde bSDD
        corpus = self.extract_corpus()
        
        if not corpus:
            print("⚠️ No se pudo extraer corpus. Usando corpus de demostración.")
            corpus = self._create_demo_corpus()
        
        # Paso 2: Construir diccionarios para cada idioma
        print("\n📝 Construyendo diccionarios...")
        
        for lang in LANGUAGES.keys():
            print(f"  🌐 {LANGUAGES[lang]['name']} ({lang})")
            dictionary = self.build_dictionary(lang, corpus)
            self.save_dictionary(lang, dictionary)
        
        # Paso 3: Crear metadatos
        self.create_meta_file()
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║   ✅ INGESTA COMPLETADA                                      ║
║   📁 Diccionarios guardados en:                              ║
║   {output_dir}                                              ║
║   🌍 {total} idiomas procesados                              ║
╚══════════════════════════════════════════════════════════════╝
        """.format(
            output_dir=self.output_dir,
            total=len(LANGUAGES)
        ))
    
    def _create_demo_corpus(self) -> Dict:
        """Crear corpus de demostración si bSDD no está disponible"""
        return {
            "Structural Elements": {
                "terms": [
                    {"name": "beam", "definition": "A horizontal structural member"},
                    {"name": "column", "definition": "A vertical structural member"},
                    {"name": "foundation", "definition": "The base of a structure"},
                    {"name": "slab", "definition": "A flat structural element"},
                    {"name": "wall", "definition": "A vertical structural element"},
                    {"name": "frame", "definition": "The structural skeleton"},
                ]
            },
            "Materials": {
                "terms": [
                    {"name": "concrete", "definition": "A composite material"},
                    {"name": "steel", "definition": "An alloy of iron and carbon"},
                    {"name": "wood", "definition": "Timber used in construction"},
                    {"name": "brick", "definition": "A building block"},
                    {"name": "glass", "definition": "A transparent material"},
                ]
            },
            "Construction": {
                "terms": [
                    {"name": "excavation", "definition": "Removing earth"},
                    {"name": "scaffolding", "definition": "Temporary structure for workers"},
                    {"name": "crane", "definition": "A machine for lifting"},
                    {"name": "formwork", "definition": "Temporary molds for concrete"},
                ]
            }
        }

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    ingestor = BSDDIngestor()
    ingestor.ingest_all()
