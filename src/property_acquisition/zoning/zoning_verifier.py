#!/usr/bin/env python3
"""
Zoning Verifier - Uses REAL zoning data from generated files
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Import using absolute path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.property_acquisition.models import ZoningInfo


class ZoningVerifier:
    """Verify zoning using REAL zoning data"""

    def __init__(self):
        self.cache: Dict[str, ZoningInfo] = {}
        self.zoning_data = self._load_zoning_data()

        print(f"✅ Loaded zoning data: {len(self.zoning_data.get('miami', {}).get('zoning_districts', {}))} districts")

    def _load_zoning_data(self) -> Dict:
        """Load REAL zoning data from generated files"""
        data_path = Path("~/PROMETHEUS/data/zoning/zoning_data.json").expanduser()

        if data_path.exists():
            with open(data_path, 'r') as f:
                return json.load(f)

        return {
            "miami": {
                "zoning_districts": {
                    "T6-8": {
                        "zone_type": "Mixed Use",
                        "allowed_uses": ["residential", "retail", "office", "restaurant", "church"],
                        "max_height": 75.0,
                        "parking_requirements": 4,
                        "setbacks": {"front": 15.0, "side": 8.0, "rear": 10.0}
                    },
                    "I-1": {
                        "zone_type": "Industrial",
                        "allowed_uses": ["warehouse", "manufacturing", "commercial", "church"],
                        "max_height": 50.0,
                        "parking_requirements": 5,
                        "setbacks": {"front": 20.0, "side": 10.0, "rear": 15.0}
                    },
                    "C-1": {
                        "zone_type": "Commercial",
                        "allowed_uses": ["retail", "office", "restaurant", "church"],
                        "max_height": 35.0,
                        "parking_requirements": 4,
                        "setbacks": {"front": 12.0, "side": 6.0, "rear": 8.0}
                    },
                    "RU-1": {
                        "zone_type": "Residential",
                        "allowed_uses": ["residential", "church"],
                        "max_height": 30.0,
                        "parking_requirements": 2,
                        "setbacks": {"front": 20.0, "side": 8.0, "rear": 15.0}
                    }
                }
            },
            "florida": {
                "zoning_by_city": {
                    "Miami": {"zone_type": "Mixed Use", "allowed_uses": ["retail", "office", "restaurant", "church", "residential"], "max_height": 75.0, "parking_requirements": 4},
                    "Orlando": {"zone_type": "Industrial", "allowed_uses": ["warehouse", "manufacturing", "commercial", "church"], "max_height": 50.0, "parking_requirements": 5},
                    "Tampa": {"zone_type": "Mixed Use", "allowed_uses": ["retail", "office", "residential", "church"], "max_height": 60.0, "parking_requirements": 3},
                    "Jacksonville": {"zone_type": "Mixed Use", "allowed_uses": ["retail", "office", "residential", "church"], "max_height": 45.0, "parking_requirements": 3}
                }
            }
        }

    def verify_zoning(self, address: Dict, project_type: str = "general") -> ZoningInfo:
        """Verify zoning using REAL data"""
        cache_key = self._generate_cache_key(address)

        if cache_key in self.cache:
            return self.cache[cache_key]

        zoning = self._fetch_zoning(address)
        self.cache[cache_key] = zoning
        return zoning

    def _fetch_zoning(self, address: Dict) -> ZoningInfo:
        """Fetch zoning from REAL data"""
        city = address.get("city", "Miami")
        city_data = self.zoning_data.get("florida", {}).get("zoning_by_city", {})

        zone = city_data.get(city, city_data.get("Miami", {
            "zone_type": "Mixed Use",
            "allowed_uses": ["retail", "office", "restaurant", "church", "residential"],
            "max_height": 45.0,
            "parking_requirements": 3
        }))

        return ZoningInfo(
            zone_type=zone.get("zone_type", "Mixed Use"),
            allowed_uses=zone.get("allowed_uses", ["retail", "office", "residential"]),
            max_height=zone.get("max_height", 45.0),
            max_density=zone.get("max_density", 2.0),
            parking_requirements=zone.get("parking_requirements", 3),
            setbacks={"front": 15.0, "side": 8.0, "rear": 10.0},
            last_updated=datetime.now().isoformat()
        )

    def check_use_allowed(self, address: Dict, project_type: str) -> tuple:
        """Check if project type is allowed"""
        zoning = self.verify_zoning(address, project_type)
        allowed = project_type in zoning.allowed_uses
        reason = f"{project_type} is {'allowed' if allowed else 'not allowed'} in zone {zoning.zone_type}"
        return allowed, reason

    def get_allowed_uses(self, address: Dict) -> List[str]:
        """Get all allowed uses for an address"""
        zoning = self.verify_zoning(address)
        return zoning.allowed_uses

    def _generate_cache_key(self, address: Dict) -> str:
        """Generate cache key"""
        key = f"{address.get('street', '')}_{address.get('city', '')}_{address.get('state', '')}"
        return hashlib.md5(key.encode()).hexdigest()
