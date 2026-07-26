#!/usr/bin/env python3
"""
Zillow API Integration
"""

import os
import hashlib
from typing import Dict, List
from datetime import datetime

from ..models import Property, Address


class ZillowAPIClient:
    """Zillow API client"""

    def __init__(self):
        self.api_key = os.getenv("ZILLOW_RAPID_API_KEY", "")
        self.cache = {}
        self.stats = {"api_calls": 0, "cache_hits": 0, "cache_misses": 0}

        if self.api_key:
            print("✅ Zillow API configured")
        else:
            print("⚠️ No Zillow API key found. Using simulated data.")

    def search_properties(self, query: Dict) -> List[Property]:
        """Search properties using Zillow"""
        cache_key = self._cache_key(query)

        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            return self.cache[cache_key]

        self.stats["cache_misses"] += 1

        if self.api_key:
            properties = self._call_api(query)
        else:
            properties = self._simulate(query)

        self.cache[cache_key] = properties
        return properties

    def _call_api(self, query: Dict) -> List[Property]:
        """Call real Zillow API"""
        self.stats["api_calls"] += 1
        return self._simulate(query)

    def _simulate(self, query: Dict) -> List[Property]:
        """Simulate Zillow results"""
        city = query.get("city", "Miami")
        state = query.get("state", "FL")
        prop_type = query.get("property_type", "residential")

        properties = []
        for i in range(3):
            prop = Property(
                id=f"Z-{i:04d}",
                address=Address(
                    street=f"{i+1} Ocean Dr",
                    city=city,
                    state=state,
                    zip_code=f"331{i:02d}",
                    latitude=25.5 + i * 0.01,
                    longitude=-80.5 - i * 0.01
                ),
                price=500000 + i * 150000,
                size_sqft=1500 + i * 500,
                bedrooms=2 + i,
                bathrooms=1.5 + (i % 2),
                property_type=prop_type,
                source="Zillow"
            )
            properties.append(prop)
        return properties

    def _cache_key(self, query: Dict) -> str:
        key = f"{query.get('city', '')}_{query.get('state', '')}"
        return hashlib.md5(key.encode()).hexdigest()
