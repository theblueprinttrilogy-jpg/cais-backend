#!/usr/bin/env python3
"""
Motor de Consulta de Códigos de Construcción.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class CodeRule:
    """Representa una regla de código de construcción."""
    code_id: str
    section: str
    title: str
    content: str
    severity: str
    jurisdiction: str
    category: str
    similarity: float = 0.0

class CodeQueryEngine:
    """
    Motor de consulta de códigos de construcción.
    """
    
    def __init__(self, classified_file: str = "~/PROMETHEUS/output/classified_codes.json"):
        """
        Initialize the code query engine.
        
        Args:
            classified_file: Path to the classified codes JSON file.
        """
        self.classified_file = Path(classified_file).expanduser()
        self.codes: List[Dict] = []
        self._load_codes()
    
    def _load_codes(self):
        """Load classified codes from file."""
        if self.classified_file.exists():
            with open(self.classified_file, 'r') as f:
                data = json.load(f)
                self.codes = data.get('sections', [])
    
    def get_applicable_codes(self, location: Dict) -> List[CodeRule]:
        """
        Get codes applicable to a location.
        
        Args:
            location: Location information (state, county, city).
            
        Returns:
            List of applicable code rules.
        """
        jurisdiction = self._determine_jurisdiction(location)
        
        # Filter codes by jurisdiction
        applicable = []
        for section in self.codes:
            if section.get('jurisdiction') == jurisdiction:
                applicable.append(CodeRule(
                    code_id=section.get('code_id', ''),
                    section=section.get('section_number', ''),
                    title=section.get('title', ''),
                    content=section.get('content', ''),
                    severity=section.get('severity', 'medium'),
                    jurisdiction=section.get('jurisdiction', ''),
                    category=section.get('category', 'general')
                ))
            elif section.get('jurisdiction') == 'International':
                applicable.append(CodeRule(
                    code_id=section.get('code_id', ''),
                    section=section.get('section_number', ''),
                    title=section.get('title', ''),
                    content=section.get('content', ''),
                    severity=section.get('severity', 'medium'),
                    jurisdiction=section.get('jurisdiction', ''),
                    category=section.get('category', 'general')
                ))
        
        # Sort by severity (critical first)
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        applicable.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        return applicable[:100]  # Limit results
    
    def get_critical_rules(self, jurisdiction: Optional[str] = None) -> List[CodeRule]:
        """
        Get critical rules.
        
        Args:
            jurisdiction: Optional jurisdiction filter.
            
        Returns:
            List of critical rules.
        """
        rules = []
        
        for section in self.codes:
            if section.get('severity') in ['critical', 'high']:
                if jurisdiction and section.get('jurisdiction') != jurisdiction:
                    continue
                rules.append(CodeRule(
                    code_id=section.get('code_id', ''),
                    section=section.get('section_number', ''),
                    title=section.get('title', ''),
                    content=section.get('content', ''),
                    severity=section.get('severity', 'medium'),
                    jurisdiction=section.get('jurisdiction', ''),
                    category=section.get('category', 'general')
                ))
        
        return rules[:50]
    
    def _determine_jurisdiction(self, location: Dict) -> str:
        """
        Determine jurisdiction from location.
        
        Args:
            location: Location information.
            
        Returns:
            Jurisdiction name.
        """
        state = location.get('state', '').lower()
        country = location.get('country', '').lower()
        
        # Florida
        if state in ['fl', 'florida']:
            county = location.get('county', '').lower()
            if 'miami-dade' in county or 'dade' in county:
                return 'Florida-MiamiDade'
            return 'Florida'
        
        # California
        if state in ['ca', 'california']:
            return 'California'
        
        # International
        return 'International'
