#!/usr/bin/env python3
"""
Property Acquisition Service
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .models import Property, Address, ZoningInfo, FeasibilityAnalysis
from .parsers.query_parser import QueryParser, ParsedQuery
from .sources.property_aggregator import PropertyAggregator
from .zoning.zoning_verifier import ZoningVerifier
from .analyzers.feasibility_analyzer import FeasibilityAnalyzer
from .search_engine import SearchEngine
from .assistant import ConstructionAssistant

__all__ = [
    'Property',
    'Address',
    'ZoningInfo',
    'FeasibilityAnalysis',
    'ParsedQuery',
    'QueryParser',
    'PropertyAggregator',
    'ZoningVerifier',
    'FeasibilityAnalyzer',
    'SearchEngine',
    'ConstructionAssistant'
]
