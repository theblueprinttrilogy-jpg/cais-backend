#!/usr/bin/env python3
"""
Query Parser - Parse natural language property queries
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ParsedQuery:
    """Result of parsing a natural language query"""
    raw_query: str
    property_type: str
    project_type: str
    location: str
    city: str
    state: str
    zip_code: Optional[str] = None
    min_price: float = 0
    max_price: float = 0
    min_size_sqft: float = 0
    max_size_sqft: float = 0
    bedrooms: int = 0
    bathrooms: float = 0
    features: List[str] = field(default_factory=list)


class QueryParser:
    """Parse natural language property queries"""

    PROPERTY_TYPES = {
        "residential": ["house", "home", "apartment", "condo"],
        "commercial": ["commercial", "office", "store", "restaurant"],
        "industrial": ["warehouse", "industrial", "factory"],
        "land": ["land", "lot", "parcel"]
    }

    def parse(self, query: str) -> ParsedQuery:
        """Parse a natural language query"""
        query_lower = query.lower()

        property_type = self._detect_property_type(query_lower)
        project_type = self._detect_project_type(query_lower)
        location = self._extract_location(query_lower)
        city, state = self._extract_city_state(query_lower)
        size_min, size_max = self._extract_size(query_lower)
        price_min, price_max = self._extract_price(query_lower)
        bedrooms = self._extract_bedrooms(query_lower)
        bathrooms = self._extract_bathrooms(query_lower)
        features = self._extract_features(query_lower)

        return ParsedQuery(
            raw_query=query,
            property_type=property_type,
            project_type=project_type,
            location=location,
            city=city,
            state=state,
            min_price=price_min,
            max_price=price_max,
            min_size_sqft=size_min,
            max_size_sqft=size_max,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            features=features
        )

    def _detect_property_type(self, text: str) -> str:
        for ptype, keywords in self.PROPERTY_TYPES.items():
            if any(k in text for k in keywords):
                return ptype
        return "residential"

    def _detect_project_type(self, text: str) -> str:
        project_keywords = {
            "church": ["church", "temple"],
            "warehouse": ["warehouse", "storage"],
            "office": ["office"],
            "restaurant": ["restaurant"],
            "school": ["school"],
            "hospital": ["hospital"]
        }
        for ptype, keywords in project_keywords.items():
            if any(k in text for k in keywords):
                return ptype
        return "general"

    def _extract_location(self, text: str) -> str:
        match = re.search(r'in\s+([a-z\s]+?)(?:\s+|\s*$)', text)
        return match.group(1).strip() if match else ""

    def _extract_city_state(self, text: str) -> Tuple[str, str]:
        cities = ["miami", "orlando", "tampa", "jacksonville"]
        states = {"florida": "FL", "california": "CA", "texas": "TX"}

        city = ""
        for c in cities:
            if c in text:
                city = c.title()
                break

        state = ""
        for s, code in states.items():
            if s in text or code.lower() in text:
                state = code
                break

        return city, state

    def _extract_size(self, text: str) -> Tuple[float, float]:
        match = re.search(r'(\d+)\s*(?:sqft|sq\s*ft)', text)
        if match:
            size = float(match.group(1))
            return size, size
        return 0, 0

    def _extract_price(self, text: str) -> Tuple[float, float]:
        match = re.search(r'\$?(\d+(?:\.\d+)?)\s*(?:k|k)', text)
        if match:
            price = float(match.group(1)) * 1000
            return price, price
        return 0, 0

    def _extract_bedrooms(self, text: str) -> int:
        match = re.search(r'(\d+)\s*(?:bed|bedroom)', text)
        return int(match.group(1)) if match else 0

    def _extract_bathrooms(self, text: str) -> float:
        match = re.search(r'(\d+\.?\d*)\s*(?:bath|bathroom)', text)
        return float(match.group(1)) if match else 0

    def _extract_features(self, text: str) -> List[str]:
        features = ["pool", "garage", "garden", "elevator", "parking"]
        return [f for f in features if f in text]
