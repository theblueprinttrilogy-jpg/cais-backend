#!/usr/bin/env python3
"""
Captain Configuration - CAIS
Defines the 3 Captains and their responsibilities.
100% ENGLISH - All comments, messages, and logs in English.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class CaptainDefinition:
    """Definition of a Captain agent."""
    name: str
    display_name: str
    description: str
    keywords: List[str]
    priority: int  # 1 = highest
    agent_count: int = 10


CAPTAIN_DEFINITIONS = {
    'BuildingCodes': CaptainDefinition(
        name='BuildingCodes',
        display_name='Building Codes Captain',
        description='Responsible for structural, egres, foundation, and habitability codes.',
        keywords=[
            'structural', 'egress', 'foundation', 'habitability',
            'framing', 'load', 'bearing', 'wall', 'floor', 'roof',
            'beam', 'column', 'joist', 'truss', 'concrete', 'steel',
            'masonry', 'wood', 'framing', 'shear', 'moment', 'deflection'
        ],
        priority=1,
        agent_count=10
    ),
    
    'SafetyRegulations': CaptainDefinition(
        name='SafetyRegulations',
        display_name='Safety Regulations Captain',
        description='Responsible for fire, seismic, guard, and handrail regulations.',
        keywords=[
            'safety', 'fire', 'seismic', 'guard', 'handrail',
            'stair', 'tread', 'riser', 'landing', 'railing',
            'emergency', 'exit', 'smoke', 'alarm', 'sprinkler',
            'guardrail', 'fall', 'protection', 'hazard', 'risk'
        ],
        priority=2,
        agent_count=10
    ),
    
    'ConstructionLaws': CaptainDefinition(
        name='ConstructionLaws',
        display_name='Construction Laws Captain',
        description='Responsible for electrical, plumbing, mechanical, and energy laws.',
        keywords=[
            'electrical', 'plumbing', 'mechanical', 'energy',
            'accessibility', 'receptacle', 'outlet', 'circuit',
            'pipe', 'drain', 'vent', 'hvac', 'duct', 'insulation',
            'wiring', 'conduit', 'fixture', 'appliance', 'meter'
        ],
        priority=3,
        agent_count=10
    )
}


def get_captain_config(captain_name: str) -> Optional[CaptainDefinition]:
    """Get configuration for a specific captain."""
    return CAPTAIN_DEFINITIONS.get(captain_name)


def get_all_captains() -> List[CaptainDefinition]:
    """Get all captain definitions."""
    return list(CAPTAIN_DEFINITIONS.values())


def get_captain_keywords(captain_name: str) -> List[str]:
    """Get keywords for a specific captain."""
    config = get_captain_config(captain_name)
    return config.keywords if config else []
