#!/usr/bin/env python3
"""
Core module - CAIS system core components
"""

# Import core components
from .cais_system import CAISSystem, get_cais
from .dictionary_engine import DictionaryEngine, get_dictionary_engine
from .translation_service import TranslationService, get_translation_service

# Import logging (commented out if not available)
# from .logging_config import ForensicLogger

__all__ = [
    'CAISSystem',
    'get_cais',
    'DictionaryEngine',
    'get_dictionary_engine',
    'TranslationService',
    'get_translation_service',
]
