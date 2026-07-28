#!/usr/bin/env python3
"""
Semantic Dictionary Manager - CAIS
Manages multilingual semantic dictionaries for construction terminology.
Downloads and caches dictionaries by language.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Language detection
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0


@dataclass
class SemanticDictionary:
    """Semantic dictionary for a specific language."""
    language_code: str
    language_name: str
    terms: Dict[str, List[str]]  # English term -> translations/synonyms
    categories: Dict[str, List[str]]  # Category -> terms
    technical_terms: List[str]
    common_phrases: List[str]
    severity_keywords: Dict[str, List[str]]  # severity -> keywords
    source: str = 'builtin'
    version: str = '1.0'
    downloaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    hash: str = ''


class SemanticDictionaryManager:
    """
    Manages semantic dictionaries for multiple languages.
    Downloads and caches dictionaries for construction terminology.
    """
    
    SUPPORTED_LANGUAGES = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
        'pt': 'Portuguese', 'it': 'Italian', 'nl': 'Dutch', 'ru': 'Russian',
        'ja': 'Japanese', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi'
    }
    
    # ============================================================
    # BUILT-IN CONSTRUCTION TERMINOLOGY (ENGLISH BASE)
    # ============================================================
    
    BUILTIN_TERMS = {
        'en': {
            'terms': {
                # Egress
                'door': ['door', 'exit', 'egress', 'entrance', 'doorway', 'portal'],
                'width': ['width', 'opening', 'span', 'clearance', 'breadth'],
                'exit_access': ['exit access', 'means of egress', 'escape route'],
                
                # Safety
                'guard': ['guard', 'guardrail', 'railing', 'barrier', 'protection'],
                'handrail': ['handrail', 'hand rail', 'grab bar', 'railing'],
                'stair': ['stair', 'stairs', 'stairway', 'step', 'flight'],
                'tread': ['tread', 'step', 'walking surface', 'floor'],
                'riser': ['riser', 'vertical', 'height', 'rise'],
                
                # Fire Protection
                'fire': ['fire', 'fire protection', 'fire safety', 'flame', 'combustion'],
                'smoke': ['smoke', 'fire alarm', 'detection', 'sensor'],
                'sprinkler': ['sprinkler', 'fire suppression', 'water system'],
                'extinguisher': ['extinguisher', 'fire extinguisher', 'suppression'],
                
                # Electrical
                'electrical': ['electrical', 'electric', 'wiring', 'circuit', 'power'],
                'receptacle': ['receptacle', 'outlet', 'socket', 'plug'],
                'circuit': ['circuit', 'breaker', 'panel', 'distribution'],
                
                # Plumbing
                'plumbing': ['plumbing', 'pipe', 'drain', 'vent', 'water supply'],
                'fixture': ['fixture', 'sink', 'toilet', 'shower', 'tub'],
                'drain': ['drain', 'waste', 'sewer', 'disposal'],
                
                # Structural
                'structural': ['structural', 'beam', 'column', 'foundation', 'framing'],
                'beam': ['beam', 'girder', 'joist', 'truss', 'rafter'],
                'column': ['column', 'pillar', 'post', 'support'],
                'foundation': ['foundation', 'footing', 'base', 'slab'],
                
                # General
                'ceiling': ['ceiling', 'overhead', 'height', 'clearance'],
                'height': ['height', 'elevation', 'clearance', 'vertical'],
                'accessibility': ['accessibility', 'accessible', 'wheelchair', 'ramp', 'disabled'],
                'energy': ['energy', 'efficiency', 'insulation', 'thermal', 'solar'],
                'ventilation': ['ventilation', 'vent', 'air', 'exhaust', 'intake']
            },
            'categories': {
                'egress': ['door', 'exit', 'egress', 'width', 'opening', 'exit_access'],
                'safety': ['guard', 'handrail', 'protection', 'barrier', 'fall'],
                'stair': ['stair', 'tread', 'riser', 'landing', 'railing'],
                'fire': ['fire', 'smoke', 'sprinkler', 'extinguisher', 'alarm'],
                'electrical': ['electrical', 'receptacle', 'circuit', 'panel', 'wire'],
                'plumbing': ['plumbing', 'fixture', 'drain', 'pipe', 'vent'],
                'structural': ['structural', 'beam', 'column', 'foundation', 'framing'],
                'general': ['ceiling', 'height', 'accessibility', 'energy', 'ventilation']
            },
            'severity_keywords': {
                'critical': ['shall', 'must', 'required', 'minimum', 'maximum', 'not less than', 'not exceed'],
                'high': ['should', 'recommended', 'advisable', 'important'],
                'medium': ['may', 'could', 'should consider', 'typical'],
                'low': ['optional', 'suggested', 'if possible']
            }
        }
    }
    
    # Translations for Spanish (example)
    BUILTIN_TERMS_ES = {
        'terms': {
            'door': ['puerta', 'salida', 'egreso', 'entrada'],
            'width': ['ancho', 'abertura', 'claro', 'dimensión'],
            'guard': ['guardia', 'barandilla', 'protección', 'barrera'],
            'handrail': ['pasamanos', 'barandilla', 'agarradera'],
            'stair': ['escalera', 'gradas', 'peldaños'],
            'tread': ['huella', 'peldaño', 'superficie de paso'],
            'riser': ['contrahuella', 'vertical', 'altura'],
            'fire': ['fuego', 'incendio', 'protección contra incendios'],
            'smoke': ['humo', 'alarma', 'detección'],
            'sprinkler': ['rociador', 'sprinkler', 'supresión de incendios'],
            'electrical': ['eléctrico', 'cableado', 'circuito'],
            'plumbing': ['plomería', 'tubería', 'desagüe', 'ventilación'],
            'structural': ['estructural', 'viga', 'columna', 'cimentación'],
            'ceiling': ['techo', 'altura', 'cielo raso'],
            'accessibility': ['accesibilidad', 'accesible', 'rampa']
        },
        'categories': {
            'egress': ['puerta', 'salida', 'egreso', 'ancho'],
            'safety': ['barandilla', 'protección', 'seguridad'],
            'stair': ['escalera', 'huella', 'contrahuella'],
            'fire': ['fuego', 'incendio', 'humo', 'rociador'],
            'electrical': ['eléctrico', 'circuito', 'cableado'],
            'plumbing': ['plomería', 'tubería', 'desagüe'],
            'structural': ['estructural', 'viga', 'columna', 'cimentación'],
            'general': ['techo', 'altura', 'accesibilidad']
        },
        'severity_keywords': {
            'critical': ['debe', 'obligatorio', 'requerido', 'mínimo', 'máximo'],
            'high': ['debería', 'recomendado', 'importante'],
            'medium': ['puede', 'podría', 'considerar'],
            'low': ['opcional', 'sugerido']
        }
    }
    
    def __init__(self, cache_dir: str = "./semantic_dictionaries"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.dictionaries: Dict[str, SemanticDictionary] = {}
        self._load_cached_dictionaries()
    
    def _load_cached_dictionaries(self):
        """Load cached dictionaries from disk."""
        for lang_file in self.cache_dir.glob("*.json"):
            try:
                with open(lang_file, 'r') as f:
                    data = json.load(f)
                    lang_code = lang_file.stem
                    if lang_code in self.SUPPORTED_LANGUAGES:
                        dict_obj = SemanticDictionary(
                            language_code=lang_code,
                            language_name=self.SUPPORTED_LANGUAGES[lang_code],
                            terms=data.get('terms', {}),
                            categories=data.get('categories', {}),
                            technical_terms=data.get('technical_terms', []),
                            common_phrases=data.get('common_phrases', []),
                            severity_keywords=data.get('severity_keywords', {}),
                            source=data.get('source', 'builtin'),
                            version=data.get('version', '1.0'),
                            downloaded_at=data.get('downloaded_at', datetime.now().isoformat()),
                            hash=data.get('hash', '')
                        )
                        self.dictionaries[lang_code] = dict_obj
            except Exception as e:
                print(f"⚠️ Could not load dictionary for {lang_file}: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of a text.
        """
        if not text or len(text.strip()) < 10:
            return 'en'
        try:
            detected = detect(text)
            if detected in self.SUPPORTED_LANGUAGES:
                return detected
            return 'en'
        except:
            return 'en'
    
    def get_dictionary(self, language_code: str) -> SemanticDictionary:
        """
        Get dictionary for a specific language.
        """
        # If already loaded, return it
        if language_code in self.dictionaries:
            return self.dictionaries[language_code]
        
        # If English, use built-in
        if language_code == 'en':
            return self._build_english_dictionary()
        
        # Try to load from cache
        cache_file = self.cache_dir / f"{language_code}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    dict_obj = SemanticDictionary(
                        language_code=language_code,
                        language_name=self.SUPPORTED_LANGUAGES.get(language_code, language_code),
                        terms=data.get('terms', {}),
                        categories=data.get('categories', {}),
                        technical_terms=data.get('technical_terms', []),
                        common_phrases=data.get('common_phrases', []),
                        severity_keywords=data.get('severity_keywords', {}),
                        source=data.get('source', 'cached'),
                        version=data.get('version', '1.0'),
                        downloaded_at=data.get('downloaded_at', datetime.now().isoformat()),
                        hash=data.get('hash', '')
                    )
                    self.dictionaries[language_code] = dict_obj
                    return dict_obj
            except:
                pass
        
        # Build from base + translations
        if language_code == 'es':
            return self._build_spanish_dictionary()
        
        # Default to English with note
        print(f"⚠️ No dictionary for {language_code}, using English")
        return self._build_english_dictionary()
    
    def _build_english_dictionary(self) -> SemanticDictionary:
        """Build the English semantic dictionary."""
        data = self.BUILTIN_TERMS['en']
        
        # Flatten terms into technical_terms
        all_terms = []
        for term_list in data['terms'].values():
            all_terms.extend(term_list)
        
        dict_obj = SemanticDictionary(
            language_code='en',
            language_name='English',
            terms=data['terms'],
            categories=data['categories'],
            technical_terms=list(set(all_terms)),
            common_phrases=self._extract_common_phrases(data['terms']),
            severity_keywords=data['severity_keywords'],
            source='builtin',
            version='1.0',
            downloaded_at=datetime.now().isoformat()
        )
        
        # Cache it
        self.dictionaries['en'] = dict_obj
        return dict_obj
    
    def _build_spanish_dictionary(self) -> SemanticDictionary:
        """Build the Spanish semantic dictionary."""
        # Start from English base
        en_data = self.BUILTIN_TERMS['en']
        es_data = self.BUILTIN_TERMS_ES
        
        # Combine terms
        combined_terms = {}
        for key, en_terms in en_data['terms'].items():
            es_translations = es_data['terms'].get(key, [])
            combined_terms[key] = en_terms + es_translations
        
        # Combine categories
        combined_categories = {}
        for category, terms in en_data['categories'].items():
            es_category_terms = es_data['categories'].get(category, [])
            combined_categories[category] = list(set(terms + es_category_terms))
        
        # Combined severity keywords
        combined_severity = {}
        for severity, keywords in en_data['severity_keywords'].items():
            es_keywords = es_data['severity_keywords'].get(severity, [])
            combined_severity[severity] = list(set(keywords + es_keywords))
        
        # Flatten terms
        all_terms = []
        for term_list in combined_terms.values():
            all_terms.extend(term_list)
        
        dict_obj = SemanticDictionary(
            language_code='es',
            language_name='Spanish',
            terms=combined_terms,
            categories=combined_categories,
            technical_terms=list(set(all_terms)),
            common_phrases=self._extract_common_phrases(combined_terms),
            severity_keywords=combined_severity,
            source='hybrid',
            version='1.0',
            downloaded_at=datetime.now().isoformat()
        )
        
        # Cache it
        self.dictionaries['es'] = dict_obj
        
        # Save to disk
        self._save_dictionary(dict_obj)
        
        return dict_obj
    
    def _extract_common_phrases(self, terms: Dict[str, List[str]]) -> List[str]:
        """Extract common phrases from terms."""
        phrases = []
        for key, values in terms.items():
            phrases.append(key)
            phrases.extend(values)
            # Add common variations
            for v in values:
                phrases.append(f"{key} {v}")
                phrases.append(f"{v} {key}")
        return list(set(phrases))
    
    def _save_dictionary(self, dict_obj: SemanticDictionary):
        """Save dictionary to disk."""
        cache_file = self.cache_dir / f"{dict_obj.language_code}.json"
        try:
            # Calculate hash
            content = json.dumps({
                'terms': dict_obj.terms,
                'categories': dict_obj.categories,
                'technical_terms': dict_obj.technical_terms,
                'common_phrases': dict_obj.common_phrases,
                'severity_keywords': dict_obj.severity_keywords
            }, sort_keys=True)
            dict_obj.hash = hashlib.sha256(content.encode()).hexdigest()
            
            with open(cache_file, 'w') as f:
                json.dump({
                    'terms': dict_obj.terms,
                    'categories': dict_obj.categories,
                    'technical_terms': dict_obj.technical_terms,
                    'common_phrases': dict_obj.common_phrases,
                    'severity_keywords': dict_obj.severity_keywords,
                    'source': dict_obj.source,
                    'version': dict_obj.version,
                    'downloaded_at': dict_obj.downloaded_at,
                    'hash': dict_obj.hash
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save dictionary: {e}")
    
    def translate_term(self, term: str, from_lang: str, to_lang: str = 'en') -> List[str]:
        """
        Translate a term from one language to another using dictionary.
        """
        if from_lang not in self.dictionaries:
            self.get_dictionary(from_lang)
        
        dict_obj = self.dictionaries.get(from_lang)
        if not dict_obj:
            return [term]
        
        # Find the term in the dictionary
        term_lower = term.lower()
        for key, translations in dict_obj.terms.items():
            if term_lower in [t.lower() for t in translations] or term_lower in key.lower():
                # If target is English, return the key
                if to_lang == 'en':
                    return [key]
                # Otherwise, try to find translations
                target_dict = self.dictionaries.get(to_lang)
                if target_dict and key in target_dict.terms:
                    return target_dict.terms[key]
        
        return [term]
    
    def get_semantic_similarity(self, term1: str, term2: str, language: str = 'en') -> float:
        """
        Calculate semantic similarity between two terms using dictionary.
        """
        term1_lower = term1.lower()
        term2_lower = term2.lower()
        
        if term1_lower == term2_lower:
            return 1.0
        
        dict_obj = self.dictionaries.get(language)
        if not dict_obj:
            return 0.0
        
        # Check if terms are in the same semantic group
        for key, translations in dict_obj.terms.items():
            translations_lower = [t.lower() for t in translations]
            if term1_lower in translations_lower and term2_lower in translations_lower:
                return 0.9
            if term1_lower in translations_lower and term2_lower in key.lower():
                return 0.85
            if term2_lower in translations_lower and term1_lower in key.lower():
                return 0.85
        
        # Check if terms are related through categories
        for category, terms in dict_obj.categories.items():
            terms_lower = [t.lower() for t in terms]
            if term1_lower in terms_lower and term2_lower in terms_lower:
                return 0.7
        
        # Check for substring matches
        if term1_lower in term2_lower or term2_lower in term1_lower:
            return 0.5
        
        return 0.0


async def main():
    """Test the Semantic Dictionary Manager."""
    print("\n" + "="*70)
    print(" SEMANTIC DICTIONARY MANAGER - TEST")
    print("="*70)
    
    manager = SemanticDictionaryManager()
    
    # Test language detection
    texts = [
        "This is a construction document about building codes.",
        "Este es un documento de construcción sobre códigos de edificación.",
        "This document contains door width requirements."
    ]
    
    for text in texts:
        lang = manager.detect_language(text)
        print(f"\n📝 Text: {text[:50]}...")
        print(f"   Detected language: {lang}")
        
        dict_obj = manager.get_dictionary(lang)
        print(f"   Dictionary: {dict_obj.language_name}")
        print(f"   Terms: {len(dict_obj.terms)}")
        print(f"   Categories: {len(dict_obj.categories)}")
        
        # Test translation
        if lang != 'en':
            translated = manager.translate_term("door", lang, 'en')
            print(f"   'door' translated to: {translated}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
