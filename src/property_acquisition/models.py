#!/usr/bin/env python3
"""
Property Data Models - Data structures for property acquisition
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Address:
    """Property address"""
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class Property:
    """Property listing"""
    id: str
    address: Address
    price: float
    size_sqft: float
    lot_size_sqft: Optional[float] = None
    bedrooms: int = 0
    bathrooms: float = 0
    property_type: str = "residential"
    description: str = ""
    source: str = ""
    url: str = ""
    zoning: Optional[str] = None
    year_built: Optional[int] = None
    features: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    coordinates: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ZoningInfo:
    """Zoning information for a property"""
    zone_type: str
    allowed_uses: List[str]
    max_height: float
    max_density: float
    parking_requirements: int
    setbacks: Dict[str, float]
    flood_zone: bool = False
    environmental_restrictions: List[str] = field(default_factory=list)
    historical_status: bool = False
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FeasibilityAnalysis:
    """Feasibility analysis for a property project"""
    property_id: str
    project_type: str
    property_cost: float
    construction_cost: float
    total_cost: float
    estimated_value: float
    roi: float
    zoning_approved: bool
    zoning_issues: List[str]
    recommendations: List[str]
    timeline_months: int
    risk_level: str
    score: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
