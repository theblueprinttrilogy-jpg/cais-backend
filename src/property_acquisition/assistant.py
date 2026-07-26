#!/usr/bin/env python3
"""
Construction Rules Assistant - Deterministic AI Based on Official Codes
IBC 2021, ASTM E631, Florida Building Code 2023
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.property_acquisition.zoning.zoning_verifier import ZoningVerifier
from src.property_acquisition.models import ZoningInfo


@dataclass
class ProjectOption:
    """Project option with deterministic evaluation"""
    name: str
    description: str
    allowed: bool
    requirements: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    risk_level: str = "low"
    code_reference: str = ""


class ConstructionAssistant:
    """
    Deterministic Construction Rules Assistant.
    Uses real codes: IBC 2021, ASTM E631, Florida Building Code 2023
    """

    def __init__(self):
        self.zoning = ZoningVerifier()
        self.rules = self._load_rules()
        
        # Cache for project type rules
        self._rules_cache = {}
        
        print(f"✅ Assistant loaded: {len(self.rules.get('categories', {}))} categories")
        print(f"   Source: {self.rules.get('source', 'Unknown')}")
        print(f"   Version: {self.rules.get('version', '1.0')}")

    def _load_rules(self) -> Dict:
        """Load construction rules from official code sources"""
        rules_path = Path("~/PROMETHEUS/data/rules/construction_rules.json").expanduser()

        if rules_path.exists():
            with open(rules_path, 'r') as f:
                return json.load(f)

        print("⚠️ Rules file not found. Using base structure.")
        return {
            "version": "1.0",
            "source": "Building Codes (ASTM/IBC/FL)",
            "categories": {
                "residential": {
                    "min_lot_size": 5000,
                    "max_height": 35.0,
                    "max_coverage": 0.35,
                    "setbacks": {"front": 20, "side": 8, "rear": 15},
                    "parking_spaces": 2,
                    "flood_zone_restrictions": True,
                    "references": ["IBC 2021 Section 503"]
                }
            }
        }

    def get_category_rules(self, project_type: str) -> Dict:
        """Get rules for a specific project category"""
        if project_type in self._rules_cache:
            return self._rules_cache[project_type]
        
        categories = self.rules.get("categories", {})
        rules = categories.get(project_type, categories.get("residential", {}))
        self._rules_cache[project_type] = rules
        return rules

    def analyze_project(self, address: Dict, project_type: str = "residential", **kwargs) -> Dict:
        """Analyze project and return options based on rules"""
        zoning = self.zoning.verify_zoning(address, project_type)
        property_analysis = self._analyze_property(address, zoning, kwargs)
        options = self._generate_options(property_analysis, project_type, kwargs)
        feasibility = self._assess_feasibility(property_analysis, options)

        return {
            "address": address,
            "project_type": project_type,
            "zoning": zoning.__dict__,
            "property_analysis": property_analysis,
            "options": [opt.__dict__ for opt in options],
            "feasibility": feasibility,
            "rules_version": self.rules.get("version", "1.0"),
            "rules_source": self.rules.get("source", "Unknown"),
            "timestamp": datetime.now().isoformat()
        }

    def _analyze_property(self, address: Dict, zoning: ZoningInfo, params: Dict) -> Dict:
        lot_size = params.get("lot_size", 10000)
        property_count = params.get("property_count", 1)
        return {
            "lot_size": lot_size,
            "property_count": property_count,
            "total_lot_size": lot_size * property_count,
            "zone_type": zoning.zone_type,
            "allowed_uses": zoning.allowed_uses,
            "max_height": zoning.max_height,
            "parking_requirements": zoning.parking_requirements,
            "setbacks": zoning.setbacks,
            "flood_zone": zoning.flood_zone
        }

    def _generate_options(self, analysis: Dict, project_type: str, params: Dict) -> List[ProjectOption]:
        options = []
        rules = self.get_category_rules(project_type)
        
        # Check if project type is allowed by zoning
        is_use_allowed = project_type in analysis["allowed_uses"]
        code_refs = rules.get("references", ["IBC 2021"])

        # Option 1: New Construction
        if analysis["total_lot_size"] >= rules.get("min_lot_size", 0) and analysis["max_height"] > 0:
            options.append(ProjectOption(
                name="New Construction",
                description=f"Build a new {project_type} structure on the unified lot",
                allowed=is_use_allowed,
                requirements=[
                    f"Min lot size: {rules.get('min_lot_size', 0)} sqft",
                    f"Max height: {rules.get('max_height', 0)} ft",
                    f"Setbacks: front {rules.get('setbacks', {}).get('front', 0)} ft",
                    "Building permit",
                    "Approved plans",
                    "Flood zone compliance" if rules.get("flood_zone_restrictions", False) else None
                ],
                steps=[
                    "1. Hire architect/engineer",
                    "2. Submit plans for approval",
                    "3. Apply for building permit",
                    "4. Site preparation and construction",
                    "5. Schedule inspections",
                    "6. Final inspection and certificate of occupancy"
                ],
                risk_level="low" if is_use_allowed else "high",
                code_reference=f"{code_refs[0]}"
            ))

        # Option 2: Demolition and Rebuild
        if analysis["property_count"] > 0:
            options.append(ProjectOption(
                name="Demolition and Rebuild",
                description="Demolish existing structures and build new",
                allowed=is_use_allowed,
                requirements=[
                    "Demolition permit",
                    "Building permit",
                    "Environmental review" if rules.get("flood_zone_restrictions", False) else None,
                    "Asbestos inspection (if applicable)"
                ],
                steps=[
                    "1. Obtain demolition permit",
                    "2. Conduct environmental assessment",
                    "3. Demolish existing structures",
                    "4. Site cleanup and preparation",
                    "5. Apply for building permit",
                    "6. Construct new building"
                ],
                risk_level="medium",
                code_reference=f"{code_refs[0]}"
            ))

        # Option 3: Lot Consolidation
        if analysis["property_count"] >= 2:
            options.append(ProjectOption(
                name="Lot Consolidation",
                description="Combine multiple lots into one",
                allowed=True,
                requirements=[
                    "Title review",
                    "Survey",
                    "Consolidation permit",
                    "County approval",
                    "Neighborhood notification"
                ],
                steps=[
                    "1. Hire surveyor",
                    "2. Verify title deeds",
                    "3. Prepare consolidation application",
                    "4. Submit to county planning department",
                    "5. Public notification period",
                    "6. Approval and recording"
                ],
                risk_level="medium",
                code_reference="FBC 2023 Section 3"
            ))

        # Option 4: Pool and Terrace (if residential or church)
        if project_type in ["residential", "church"] and analysis["lot_size"] >= 5000 and not analysis["flood_zone"]:
            options.append(ProjectOption(
                name="Pool and Terrace",
                description="Add swimming pool and terrace overlooking pond",
                allowed=is_use_allowed,
                requirements=[
                    "Pool permit",
                    "Setback compliance",
                    "Safety fence (required by law)",
                    "Electrical permit",
                    "Environmental review (if near water)"
                ],
                steps=[
                    "1. Design pool and terrace",
                    "2. Submit pool plans for approval",
                    "3. Apply for pool permit",
                    "4. Construction",
                    "5. Safety inspection",
                    "6. Final approval"
                ],
                risk_level="medium",
                code_reference="FBC 2023 Chapter 4"
            ))

        return options

    def _assess_feasibility(self, analysis: Dict, options: List[ProjectOption]) -> Dict:
        allowed = [opt for opt in options if opt.allowed]
        return {
            "total_options": len(options),
            "allowed_options": len(allowed),
            "is_feasible": len(allowed) > 0
        }


def main():
    assistant = ConstructionAssistant()

    address = {
        "street": "8423 Duskin Ct",
        "city": "Jacksonville",
        "state": "FL",
        "zip_code": "32216"
    }

    # Test different project types
    project_types = ["residential", "commercial", "industrial", "church", "warehouse"]

    for project_type in project_types:
        print(f"\n{'='*50}")
        print(f"📋 PROJECT: {project_type.upper()}")
        print(f"{'='*50}")

        result = assistant.analyze_project(address, project_type=project_type, lot_size=10890, property_count=3)

        print(f"📍 {address['street']}, {address['city']}, {address['state']}")
        print(f"🏷️  Zone: {result['zoning']['zone_type']}")
        print(f"📋 Allowed Uses: {', '.join(result['zoning']['allowed_uses'])}")
        print(f"📖 Rules Version: {result['rules_version']}")

        print("\n✅ OPTIONS:")
        for opt in result['options']:
            status = "✅" if opt['allowed'] else "❌"
            print(f"   {status} {opt['name']} (Risk: {opt['risk_level']})")
            print(f"      {opt['description']}")
            if opt['code_reference']:
                print(f"      Code: {opt['code_reference']}")


if __name__ == "__main__":
    main()
