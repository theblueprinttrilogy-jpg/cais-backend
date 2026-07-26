#!/usr/bin/env python3
"""
Search Engine - Unified property search and analysis
"""

from typing import Dict, List, Optional
from datetime import datetime

from .parsers.query_parser import QueryParser
from .sources.property_aggregator import PropertyAggregator
from .zoning.zoning_verifier import ZoningVerifier
from .analyzers.feasibility_analyzer import FeasibilityAnalyzer


class SearchEngine:
    """Unified search engine for property acquisition"""

    def __init__(self):
        self.parser = QueryParser()
        self.aggregator = PropertyAggregator()
        self.zoning = ZoningVerifier()
        self.analyzer = FeasibilityAnalyzer()
        self.search_history: List[Dict] = []

    def search(self, query: str, user_id: str = "anonymous") -> Dict:
        """Execute a complete property search"""
        parsed = self.parser.parse(query)
        properties = self.aggregator.search(parsed.__dict__)

        results = []
        for prop in properties:
            zoning = self.zoning.verify_zoning(prop.address.__dict__, parsed.project_type)
            feasibility = self.analyzer.analyze(prop, zoning, parsed.project_type)

            results.append({
                "property": prop,
                "zoning": zoning,
                "feasibility": feasibility
            })

        results.sort(key=lambda x: x["feasibility"].score, reverse=True)

        self.search_history.append({
            "user_id": user_id,
            "query": query,
            "results": len(results),
            "timestamp": datetime.now().isoformat()
        })

        return {
            "query": query,
            "parsed_query": {
                "property_type": parsed.property_type,
                "project_type": parsed.project_type,
                "location": parsed.location,
                "city": parsed.city,
                "state": parsed.state
            },
            "total_properties": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
