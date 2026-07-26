#!/usr/bin/env python3
"""
Translation Service - Semantic Translation Engine for CAIS
Supports: Google Translate API, DeepL API, Local Dictionary Engine
Features: Contextual Translation, Semantic Cache, Fallback Chain, Learning
"""

import os
import json
import time
import hashlib
import threading
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
import re

@dataclass
class TranslationEntry:
    """Represents a translation entry with metadata"""
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    confidence: float = 1.0
    used_api: str = "local"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: str = ""
    domain: str = "construction"

class TranslationCache:
    """
    Advanced caching system for translations
    Features: LRU eviction, TTL, persistence, semantic grouping
    """
    
    def __init__(self, cache_dir: str = "~/PROMETHEUS/data/translation_cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_cache: Dict[str, TranslationEntry] = {}
        self.max_memory_entries = 10000
        self.ttl_seconds = 86400  # 24 hours
        self._lock = threading.Lock()
        
        self._load_from_disk()
        self._stats = {"hits": 0, "misses": 0, "writes": 0}
        
        print(f"📦 TranslationCache initialized: {len(self.memory_cache)} entries loaded")
    
    def get(self, source_text: str, source_lang: str, target_lang: str, context: str = "") -> Optional[TranslationEntry]:
        """Get translation from cache"""
        key = self._generate_key(source_text, source_lang, target_lang, context)
        
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                # Check TTL
                if self._is_valid(entry):
                    self._stats["hits"] += 1
                    return entry
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
            
            self._stats["misses"] += 1
            return None
    
    def set(self, entry: TranslationEntry) -> None:
        """Store translation in cache"""
        key = self._generate_key(entry.source_text, entry.source_lang, 
                                entry.target_lang, entry.context)
        
        with self._lock:
            # Check if memory cache is full
            if len(self.memory_cache) >= self.max_memory_entries:
                self._evict_oldest()
            
            self.memory_cache[key] = entry
            self._stats["writes"] += 1
            
            # Write to disk asynchronously
            self._save_to_disk()
    
    def _generate_key(self, source_text: str, source_lang: str, target_lang: str, context: str = "") -> str:
        """Generate cache key from translation parameters"""
        normalized = source_text.lower().strip()
        if context:
            normalized += f"||{context.lower().strip()}"
        key_string = f"{source_lang}_{target_lang}_{normalized}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_valid(self, entry: TranslationEntry) -> bool:
        """Check if cache entry is still valid"""
        created = datetime.fromisoformat(entry.timestamp)
        age = (datetime.now() - created).total_seconds()
        return age < self.ttl_seconds
    
    def _evict_oldest(self) -> None:
        """Evict oldest entries from memory cache"""
        sorted_entries = sorted(self.memory_cache.items(), 
                               key=lambda x: x[1].timestamp)
        # Remove oldest 10%
        to_remove = int(len(self.memory_cache) * 0.1)
        for key, _ in sorted_entries[:to_remove]:
            del self.memory_cache[key]
    
    def _load_from_disk(self) -> None:
        """Load cache from disk"""
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data:
                        entry = TranslationEntry(**entry_data)
                        self.memory_cache[self._generate_key(
                            entry.source_text, entry.source_lang,
                            entry.target_lang, entry.context
                        )] = entry
            except Exception as e:
                print(f"⚠️ Error loading cache: {e}")
    
    def _save_to_disk(self) -> None:
        """Save cache to disk"""
        try:
            cache_file = self.cache_dir / "cache.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump([entry.__dict__ for entry in self.memory_cache.values()], 
                         f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Error saving cache: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            **self._stats,
            "total_entries": len(self.memory_cache),
            "hit_ratio": self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) 
                         if self._stats["hits"] + self._stats["misses"] > 0 else 0
        }

class SemanticTranslator:
    """
    Semantic translator with context awareness
    Handles construction-specific terminology
    """
    
    def __init__(self):
        self.semantic_rules = self._load_semantic_rules()
        self.context_patterns = self._load_context_patterns()
    
    def _load_semantic_rules(self) -> Dict:
        """Load semantic translation rules for construction"""
        return {
            "structural": {
                "beam": {"type": "structural", "unit": "linear_meter"},
                "column": {"type": "structural", "unit": "each"},
                "foundation": {"type": "structural", "unit": "cubic_meter"},
            },
            "materials": {
                "concrete": {"type": "material", "unit": "cubic_meter", "grade": "standard"},
                "steel": {"type": "material", "unit": "ton", "grade": "structural"},
                "wood": {"type": "material", "unit": "board_foot"},
            }
        }
    
    def _load_context_patterns(self) -> Dict:
        """Load context detection patterns"""
        return {
            "structural": [
                r"load|support|strength|structural|frame|column|beam|foundation",
                r"truss|girder|joist|rafter|purlin"
            ],
            "materials": [
                r"concrete|steel|wood|brick|glass|stone|asphalt|cement|mortar",
                r"material|composition|properties|strength|density"
            ],
            "construction": [
                r"excavation|scaffolding|crane|formwork|waterproofing",
                r"compaction|grading|shoring|paving"
            ],
            "safety": [
                r"safety|protection|hazard|risk|emergency|guardrail",
                r"ppe|harness|netting|guardrail"
            ],
            "legal": [
                r"permit|inspection|code|zoning|regulation|compliance",
                r"jurisdiction|ordinance|statute|liability"
            ]
        }
    
    def detect_context(self, text: str) -> str:
        """Detect construction context from text"""
        text_lower = text.lower()
        scores = defaultdict(int)
        
        for context, patterns in self.context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    scores[context] += 1
        
        if scores:
            return max(scores, key=scores.get)
        return "general"
    
    def enhance_translation(self, text: str, target_lang: str, context: str = "") -> Dict:
        """
        Enhance translation with semantic information
        """
        return {
            "original": text,
            "context": context or self.detect_context(text),
            "semantic_rules": self.semantic_rules,
            "target_language": target_lang,
            "timestamp": datetime.now().isoformat()
        }

class TranslationService:
    """
    Complete Translation Service with:
    - Google Translate API
    - DeepL API
    - Local Dictionary Engine
    - Semantic Translation
    - Cache System
    - Learning Capabilities
    """
    
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
        self.deepl_api_key = os.getenv("DEEPL_API_KEY", "")
        
        self.use_google = bool(self.google_api_key)
        self.use_deepl = bool(self.deepl_api_key)
        
        # Initialize components
        self.cache = TranslationCache()
        self.semantic = SemanticTranslator()
        
        # Import dictionary engine
        from dictionary_engine import get_dictionary_engine
        self.dict_engine = get_dictionary_engine()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "api_google_used": 0,
            "api_deepl_used": 0,
            "api_failures": 0,
            "fallback_used": 0,
            "semantic_enhancements": 0
        }
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║   🌐 TRANSLATION SERVICE INITIALIZED                        ║
║   Google API: {'✅' if self.use_google else '❌'}                           ║
║   DeepL API: {'✅' if self.use_deepl else '❌'}                             ║
║   Semantic Engine: ✅                                      ║
║   Cache: {len(self.cache.memory_cache)} entries loaded               ║
║   Fallback: Local Dictionary Engine                        ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def translate(self, text: str, target_lang: str, 
                  source_lang: str = "en", context: str = "") -> Dict:
        """
        Translate text with full semantic pipeline
        Returns detailed translation result with metadata
        """
        self.stats["total_requests"] += 1
        
        # Check cache
        cached = self.cache.get(text, source_lang, target_lang, context)
        if cached:
            return {
                "success": True,
                "translation": cached.target_text,
                "source": "cache",
                "confidence": cached.confidence,
                "metadata": {
                    "cached_at": cached.timestamp,
                    "used_api": cached.used_api,
                    "context": context
                }
            }
        
        # Detect context
        detected_context = context or self.semantic.detect_context(text)
        
        # Try APIs
        result = None
        used_api = "local"
        confidence = 0.8
        
        # Try Google
        if self.use_google:
            result = self._translate_google(text, target_lang, source_lang)
            if result:
                used_api = "google"
                confidence = 0.95
                self.stats["api_google_used"] += 1
        
        # Try DeepL (if Google failed or not available)
        if not result and self.use_deepl:
            result = self._translate_deepl(text, target_lang, source_lang)
            if result:
                used_api = "deepl"
                confidence = 0.93
                self.stats["api_deepl_used"] += 1
        
        # Fallback to local
        if not result:
            result = self._translate_local(text, target_lang, source_lang)
            confidence = 0.7
            self.stats["fallback_used"] += 1
            self.stats["api_failures"] += 1
        
        # Create cache entry
        entry = TranslationEntry(
            source_text=text,
            target_text=result,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=confidence,
            used_api=used_api,
            context=detected_context
        )
        self.cache.set(entry)
        
        # Semantic enhancement
        semantic_info = self.semantic.enhance_translation(result, target_lang, detected_context)
        self.stats["semantic_enhancements"] += 1
        
        return {
            "success": True,
            "translation": result,
            "source": used_api,
            "confidence": confidence,
            "metadata": {
                "context": detected_context,
                "semantic": semantic_info,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _translate_google(self, text: str, target_lang: str, source_lang: str) -> Optional[str]:
        """Translate using Google Translate API with retry logic"""
        if not self.google_api_key:
            return None
        
        for attempt in range(3):
            try:
                url = "https://translation.googleapis.com/language/translate/v2"
                params = {
                    "key": self.google_api_key,
                    "q": text,
                    "target": target_lang,
                    "source": source_lang
                }
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["data"]["translations"][0]["translatedText"]
                elif response.status_code == 429:
                    # Rate limit - wait and retry
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                    continue
                print(f"⚠️ Google API error (attempt {attempt+1}): {e}")
                return None
        
        return None
    
    def _translate_deepl(self, text: str, target_lang: str, source_lang: str) -> Optional[str]:
        """Translate using DeepL API with retry logic"""
        if not self.deepl_api_key:
            return None
        
        for attempt in range(3):
            try:
                url = "https://api-free.deepl.com/v2/translate"
                params = {
                    "auth_key": self.deepl_api_key,
                    "text": text,
                    "target_lang": target_lang.upper(),
                    "source_lang": source_lang.upper()
                }
                
                response = requests.post(url, data=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["translations"][0]["text"]
                elif response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return None
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                    continue
                print(f"⚠️ DeepL API error (attempt {attempt+1}): {e}")
                return None
        
        return None
    
    def _translate_local(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using local dictionary engine"""
        words = text.split()
        translated_words = []
        
        for word in words:
            # Handle punctuation
            clean_word = word.strip(".,!?;:()\"'")
            punctuation = word.replace(clean_word, "")
            
            translated = self.dict_engine.translate_term(clean_word, source_lang, target_lang)
            translated_words.append(translated + punctuation)
        
        return " ".join(translated_words)
    
    def translate_construction_term(self, term: str, target_lang: str) -> str:
        """Specialized translation for construction terms"""
        return self.dict_engine.translate_term(term, "en", target_lang)
    
    def get_term_definition(self, term: str, language: str = "en") -> str:
        """Get definition in target language"""
        definition = self.dict_engine.get_term_definition(term, "en")
        if language != "en":
            result = self.translate(definition, language, "en")
            return result.get("translation", definition)
        return definition
    
    def learn_translation(self, source: str, target: str, source_lang: str, target_lang: str) -> None:
        """Learn a new translation pair for future use"""
        entry = TranslationEntry(
            source_text=source,
            target_text=target,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=0.85,
            used_api="learning"
        )
        self.cache.set(entry)
    
    def get_stats(self) -> Dict:
        """Get complete service statistics"""
        return {
            **self.stats,
            "cache": self.cache.get_stats(),
            "api_available": {
                "google": self.use_google,
                "deepl": self.use_deepl
            }
        }

# Singleton instance
_translation_service = None

def get_translation_service() -> TranslationService:
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
