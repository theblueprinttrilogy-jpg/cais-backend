#!/usr/bin/env python3
"""
Configuración de fuentes de códigos de construcción para Florida y California.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CodeSource:
    """Representa una fuente de código de construcción."""
    name: str
    jurisdiction: str
    version: str
    url: str
    modules: List[str]
    category: str  # 'hurricane', 'seismic', 'general'
    priority: int  # 1 = más crítico

# Fuentes de códigos de Florida (Huracanes)
FLORIDA_SOURCES = [
    CodeSource(
        name="FBC Building 2023",
        jurisdiction="Florida",
        version="2023",
        url="https://www.floridabuilding.org/fbc/",
        modules=["Building", "Residential", "Existing Building"],
        category="hurricane",
        priority=1
    ),
    CodeSource(
        name="FBC HVHZ 2023",
        jurisdiction="Florida-HVHZ",
        version="2023",
        url="https://www.floridabuilding.org/fbc/",
        modules=["Building", "Residential"],
        category="hurricane",
        priority=1
    ),
    CodeSource(
        name="Miami-Dade Amendments 2023",
        jurisdiction="Florida-MiamiDade",
        version="2023",
        url="https://www.miamidade.gov/building/",
        modules=["Building", "Residential", "Energy"],
        category="hurricane",
        priority=1
    ),
    CodeSource(
        name="ASCE 7-22 Wind Loads",
        jurisdiction="Florida",
        version="2022",
        url="https://www.asce.org/",
        modules=["Wind Loads", "Structural"],
        category="hurricane",
        priority=1
    ),
]

# Fuentes de códigos de California (Terremotos)
CALIFORNIA_SOURCES = [
    CodeSource(
        name="CBC Building 2022",
        jurisdiction="California",
        version="2022",
        url="https://www.dgs.ca.gov/BSC",
        modules=["Building", "Residential", "Existing Building"],
        category="seismic",
        priority=1
    ),
    CodeSource(
        name="CBC Seismic Design",
        jurisdiction="California",
        version="2022",
        url="https://www.dgs.ca.gov/BSC",
        modules=["Seismic", "Structural"],
        category="seismic",
        priority=1
    ),
    CodeSource(
        name="CBC Title 24 Energy",
        jurisdiction="California",
        version="2022",
        url="https://www.energy.ca.gov/programs-and-topics/programs/building-energy-efficiency-standards",
        modules=["Energy", "Residential", "Non-Residential"],
        category="seismic",
        priority=2
    ),
    CodeSource(
        name="ASCE 7-22 Seismic Loads",
        jurisdiction="California",
        version="2022",
        url="https://www.asce.org/",
        modules=["Seismic Loads", "Structural"],
        category="seismic",
        priority=1
    ),
]

# Códigos generales aplicables a ambas jurisdicciones
GENERAL_SOURCES = [
    CodeSource(
        name="IBC 2021",
        jurisdiction="International",
        version="2021",
        url="https://www.iccsafe.org/",
        modules=["Building", "Structural", "Fire"],
        category="general",
        priority=2
    ),
    CodeSource(
        name="NFPA 101 2021",
        jurisdiction="International",
        version="2021",
        url="https://www.nfpa.org/",
        modules=["Life Safety", "Fire"],
        category="general",
        priority=2
    ),
]

ALL_SOURCES = FLORIDA_SOURCES + CALIFORNIA_SOURCES + GENERAL_SOURCES
