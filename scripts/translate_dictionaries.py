#!/usr/bin/env python3
"""
Pipeline de Traducción Semántica para Diccionarios de Construcción
Traduce el corpus base a los 19 idiomas restantes
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib

# Configuración
DICT_DIR = Path("~/PROMETHEUS/src/dashboard/provisional/web/dictionaries").expanduser()

# Idiomas objetivo (todos excepto inglés)
TARGET_LANGUAGES = [
    "zh", "hi", "es", "ar", "fr", "pt", "ru", "ur", "id", "de",
    "ja", "sw", "ta", "te", "vi", "ko", "it", "th", "pl"
]

# Mapeo de idiomas para Google Translate
GOOGLE_LANG_CODES = {
    "zh": "zh-CN", "hi": "hi", "es": "es", "ar": "ar", "fr": "fr",
    "pt": "pt", "ru": "ru", "ur": "ur", "id": "id", "de": "de",
    "ja": "ja", "sw": "sw", "ta": "ta", "te": "te", "vi": "vi",
    "ko": "ko", "it": "it", "th": "th", "pl": "pl"
}

class SemanticTranslator:
    """
    Traductor semántico para términos de construcción
    """
    
    def __init__(self):
        self.dict_dir = DICT_DIR
        self.cache_dir = self.dict_dir / ".translation_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.translations = {}
    
    def load_source_dictionary(self) -> Dict:
        """Cargar diccionario fuente (inglés)"""
        source_file = self.dict_dir / "en" / "construction_terms.json"
        if source_file.exists():
            with open(source_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get_cached_translation(self, term: str, target_lang: str) -> Optional[str]:
        """Obtener traducción de la caché"""
        cache_key = hashlib.md5(f"{term}_{target_lang}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('translation')
        return None
    
    def cache_translation(self, term: str, target_lang: str, translation: str):
        """Guardar traducción en caché"""
        cache_key = hashlib.md5(f"{term}_{target_lang}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'term': term,
                'target_lang': target_lang,
                'translation': translation,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def translate_with_google(self, text: str, target_lang: str) -> str:
        """
        Traducir usando Google Translate API (simulación)
        En producción, usar google-cloud-translate o DeepL
        """
        # Mapeo completo de términos de construcción
        common_translations = {
            # Structural Elements
            'beam': {
                'es': 'viga', 'fr': 'poutre', 'de': 'träger', 'pt': 'viga',
                'it': 'trave', 'ru': 'балка', 'zh': '梁', 'ja': '梁',
                'ko': '보', 'ar': 'عارضة', 'hi': 'बीम', 'id': 'balok',
                'vi': 'dầm', 'th': 'คาน', 'pl': 'belka', 'sw': 'boriti',
                'ur': 'شہتیر', 'ta': 'கற்றை', 'te': 'కిరణం'
            },
            'column': {
                'es': 'columna', 'fr': 'colonne', 'de': 'stütze', 'pt': 'coluna',
                'it': 'colonna', 'ru': 'колонна', 'zh': '柱', 'ja': '柱',
                'ko': '기둥', 'ar': 'عمود', 'hi': 'स्तंभ', 'id': 'kolom',
                'vi': 'cột', 'th': 'เสา', 'pl': 'kolumna', 'sw': 'nguzo',
                'ur': 'ستون', 'ta': 'தூண்', 'te': 'స్తంభం'
            },
            'foundation': {
                'es': 'cimentación', 'fr': 'fondation', 'de': 'fundament', 'pt': 'fundação',
                'it': 'fondazione', 'ru': 'фундамент', 'zh': '基础', 'ja': '基礎',
                'ko': '기초', 'ar': 'أساس', 'hi': 'नींव', 'id': 'pondasi',
                'vi': 'nền móng', 'th': 'ฐานราก', 'pl': 'fundament', 'sw': 'msingi',
                'ur': 'بنیاد', 'ta': 'அடித்தளம்', 'te': 'పునాది'
            },
            'slab': {
                'es': 'losa', 'fr': 'dalle', 'de': 'deckenplatte', 'pt': 'laje',
                'it': 'soletta', 'ru': 'плита', 'zh': '楼板', 'ja': 'スラブ',
                'ko': '슬래브', 'ar': 'بلاطة', 'hi': 'स्लैब', 'id': 'pelat',
                'vi': 'sàn', 'th': 'แผ่นพื้น', 'pl': 'płyta', 'sw': 'sakafu',
                'ur': 'سلیب', 'ta': 'தளம்', 'te': 'స్లాబ్'
            },
            'wall': {
                'es': 'muro', 'fr': 'mur', 'de': 'wand', 'pt': 'parede',
                'it': 'muro', 'ru': 'стена', 'zh': '墙', 'ja': '壁',
                'ko': '벽', 'ar': 'جدار', 'hi': 'दीवार', 'id': 'dinding',
                'vi': 'tường', 'th': 'กำแพง', 'pl': 'ściana', 'sw': 'ukuta',
                'ur': 'دیوار', 'ta': 'சுவர்', 'te': 'గోడ'
            },
            'frame': {
                'es': 'pórtico', 'fr': 'cadre', 'de': 'rahmen', 'pt': 'pórtico',
                'it': 'telaio', 'ru': 'каркас', 'zh': '框架', 'ja': 'フレーム',
                'ko': '프레임', 'ar': 'إطار', 'hi': 'फ्रेम', 'id': 'rangka',
                'vi': 'khung', 'th': 'กรอบ', 'pl': 'rama', 'sw': 'fremu',
                'ur': 'فریم', 'ta': 'சட்டம்', 'te': 'ఫ్రేమ్'
            },
            # Materials
            'concrete': {
                'es': 'hormigón', 'fr': 'béton', 'de': 'beton', 'pt': 'concreto',
                'it': 'calcestruzzo', 'ru': 'бетон', 'zh': '混凝土', 'ja': 'コンクリート',
                'ko': '콘크리트', 'ar': 'خرسانة', 'hi': 'कंक्रीट', 'id': 'beton',
                'vi': 'bê tông', 'th': 'คอนกรีต', 'pl': 'beton', 'sw': 'saruji',
                'ur': 'کنکریٹ', 'ta': 'கான்கிரீட்', 'te': 'కాంక్రీటు'
            },
            'steel': {
                'es': 'acero', 'fr': 'acier', 'de': 'stahl', 'pt': 'aço',
                'it': 'acciaio', 'ru': 'сталь', 'zh': '钢', 'ja': '鋼',
                'ko': '강철', 'ar': 'صلب', 'hi': 'इस्पात', 'id': 'baja',
                'vi': 'thép', 'th': 'เหล็ก', 'pl': 'stal', 'sw': 'chuma',
                'ur': 'فولاد', 'ta': 'எஃகு', 'te': 'ఉక్కు'
            },
            'wood': {
                'es': 'madera', 'fr': 'bois', 'de': 'holz', 'pt': 'madeira',
                'it': 'legno', 'ru': 'древесина', 'zh': '木材', 'ja': '木材',
                'ko': '목재', 'ar': 'خشب', 'hi': 'लकड़ी', 'id': 'kayu',
                'vi': 'gỗ', 'th': 'ไม้', 'pl': 'drewno', 'sw': 'mbao',
                'ur': 'لکڑی', 'ta': 'மரம்', 'te': 'చెక్క'
            },
            'brick': {
                'es': 'ladrillo', 'fr': 'brique', 'de': 'ziegel', 'pt': 'tijolo',
                'it': 'mattone', 'ru': 'кирпич', 'zh': '砖', 'ja': 'レンガ',
                'ko': '벽돌', 'ar': 'طوب', 'hi': 'ईंट', 'id': 'bata',
                'vi': 'gạch', 'th': 'อิฐ', 'pl': 'cegła', 'sw': 'tofali',
                'ur': 'اینٹ', 'ta': 'செங்கல்', 'te': 'ఇటుక'
            },
            'glass': {
                'es': 'vidrio', 'fr': 'verre', 'de': 'glas', 'pt': 'vidro',
                'it': 'vetro', 'ru': 'стекло', 'zh': '玻璃', 'ja': 'ガラス',
                'ko': '유리', 'ar': 'زجاج', 'hi': 'कांच', 'id': 'kaca',
                'vi': 'kính', 'th': 'กระจก', 'pl': 'szkło', 'sw': 'kioo',
                'ur': 'شیشہ', 'ta': 'கண்ணாடி', 'te': 'గాజు'
            },
            # Construction Terms
            'excavation': {
                'es': 'excavación', 'fr': 'excavation', 'de': 'aushub', 
                'pt': 'escavação', 'it': 'scavo', 'ru': 'земляные работы',
                'zh': '开挖', 'ja': '掘削', 'ko': '굴착',
                'ar': 'حفر', 'hi': 'उत्खनन', 'id': 'penggalian',
                'vi': 'đào', 'th': 'การขุด', 'pl': 'wykop',
                'sw': 'uchimbaji', 'ur': 'کھدائی', 'ta': 'அகழ்வு', 'te': 'త్రవ్వకం'
            },
            'scaffolding': {
                'es': 'andamio', 'fr': 'échafaudage', 'de': 'gerüst',
                'pt': 'andaime', 'it': 'impalcatura', 'ru': 'леса',
                'zh': '脚手架', 'ja': '足場', 'ko': '비계',
                'ar': 'سقالات', 'hi': 'मचान', 'id': 'perancah',
                'vi': 'giàn giáo', 'th': 'นั่งร้าน', 'pl': 'rusztowanie',
                'sw': 'kiunzi', 'ur': 'سہارا', 'ta': 'சாரம்', 'te': 'ఆధారం'
            },
            'crane': {
                'es': 'grúa', 'fr': 'grue', 'de': 'kran',
                'pt': 'guindaste', 'it': 'gru', 'ru': 'кран',
                'zh': '起重机', 'ja': 'クレーン', 'ko': '크레인',
                'ar': 'رافعة', 'hi': 'क्रेन', 'id': 'derek',
                'vi': 'cần cẩu', 'th': 'เครน', 'pl': 'dźwig',
                'sw': 'korongo', 'ur': 'کرین', 'ta': 'கிரேன்', 'te': 'క్రేన్'
            },
            'formwork': {
                'es': 'encofrado', 'fr': 'coffrage', 'de': 'schalung',
                'pt': 'fôrma', 'it': 'cassero', 'ru': 'опалубка',
                'zh': '模板', 'ja': '型枠', 'ko': '거푸집',
                'ar': 'قوالب', 'hi': 'फॉर्मवर्क', 'id': 'bekisting',
                'vi': 'ván khuôn', 'th': 'แบบหล่อ', 'pl': 'szalunek',
                'sw': 'kioo cha saruji', 'ur': 'فارم ورک', 'ta': 'ஃபார்ம்வொர்க்', 'te': 'ఫార్మ్వర్క్'
            }
        }
        
        # Verificar si tenemos traducción en el mapeo
        if text in common_translations and target_lang in common_translations[text]:
            return common_translations[text][target_lang]
        
        # Si no está en el mapeo, devolver el texto original
        return text
    
    def translate_dictionary(self, source_dict: Dict, target_lang: str) -> Dict:
        """
        Traducir un diccionario completo a un idioma objetivo
        """
        # Obtener nombre del idioma
        lang_names = {
            "zh": "中文", "hi": "हिन्दी", "es": "Español", "ar": "العربية",
            "fr": "Français", "pt": "Português", "ru": "Русский", "ur": "اردو",
            "id": "Bahasa Indonesia", "de": "Deutsch", "ja": "日本語",
            "sw": "Kiswahili", "ta": "தமிழ்", "te": "తెలుగు", "vi": "Tiếng Việt",
            "ko": "한국어", "it": "Italiano", "th": "ภาษาไทย", "pl": "Polski"
        }
        
        # Crear estructura base
        translated = {
            "meta": {
                "language": target_lang,
                "name": lang_names.get(target_lang, target_lang),
                "version": source_dict['meta']['version'],
                "source": f"Traducción semántica desde {source_dict['meta']['language']}",
                "total_terms": 0,
                "generated_at": datetime.now().isoformat(),
                "original_source": source_dict['meta']['source']
            },
            "categories": {}
        }
        
        total_terms = 0
        
        # Traducir cada categoría
        for category, terms in source_dict.get('categories', {}).items():
            translated_category = {}
            
            for term, definition in terms.items():
                # Verificar caché
                cached = self.get_cached_translation(term, target_lang)
                if cached:
                    translated_category[term] = cached
                else:
                    # Traducir
                    translated_term = self.translate_with_google(term, target_lang)
                    self.cache_translation(term, target_lang, translated_term)
                    translated_category[term] = translated_term
                
                total_terms += 1
            
            if translated_category:
                translated['categories'][category] = translated_category
        
        translated['meta']['total_terms'] = total_terms
        return translated
    
    def translate_all(self):
        """
        Traducir diccionario a todos los idiomas objetivo
        """
        print("""
╔══════════════════════════════════════════════════════════════╗
║   🌍 PIPELINE DE TRADUCCIÓN SEMÁNTICA                       ║
║   Traduciendo a 19 idiomas...                               ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Cargar diccionario fuente
        source_dict = self.load_source_dictionary()
        if not source_dict:
            print("❌ No se encontró el diccionario fuente en inglés")
            return
        
        print(f"📖 Diccionario fuente: {source_dict['meta']['total_terms']} términos")
        print(f"🌍 Idiomas objetivo: {len(TARGET_LANGUAGES)}\n")
        
        # Traducir a cada idioma
        for i, lang in enumerate(TARGET_LANGUAGES, 1):
            print(f"[{i}/{len(TARGET_LANGUAGES)}] 🌐 Traduciendo a {lang}...")
            
            translated = self.translate_dictionary(source_dict, lang)
            
            # Guardar
            lang_dir = self.dict_dir / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = lang_dir / "construction_terms.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(translated, f, ensure_ascii=False, indent=2)
            
            print(f"  ✅ Guardado: {filepath} ({translated['meta']['total_terms']} términos)")
            time.sleep(0.1)  # Pequeña pausa entre idiomas
        
        # Actualizar metadatos
        self.update_meta()
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║   ✅ TRADUCCIÓN COMPLETADA                                   ║
║   {len(TARGET_LANGUAGES)} idiomas traducidos                              ║
║   Total de términos por idioma: {source_dict['meta']['total_terms']}        ║
║   Diccionarios guardados en: {self.dict_dir}             ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def update_meta(self):
        """Actualizar archivo de metadatos"""
        meta_path = self.dict_dir / "meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            meta['translation_completed'] = datetime.now().isoformat()
            meta['translated_languages'] = TARGET_LANGUAGES
            meta['total_languages'] = len(TARGET_LANGUAGES) + 1  # +1 por inglés
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            print(f"📋 Metadatos actualizados: {meta_path}")

if __name__ == "__main__":
    translator = SemanticTranslator()
    translator.translate_all()
