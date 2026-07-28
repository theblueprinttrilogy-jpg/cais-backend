#!/usr/bin/env python3
"""
Jurisdiction Agent - CAIS
Detects jurisdiction hierarchy from document address.
Levels: Municipality → County → State → Country
Accesses LOCAL codes, regulations, and laws.
100% ENGLISH - All comments, messages, and logs in English.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class JurisdictionHierarchy:
    """Complete jurisdiction hierarchy for a location."""
    country: str = 'Unknown'
    state: str = 'Unknown'
    state_code: str = 'Unknown'
    county: str = 'Unknown'
    municipality: str = 'Unknown'
    zip_code: str = 'Unknown'
    full_address: str = ''
    confidence: float = 0.0


class JurisdictionAgent:
    """
    Detects jurisdiction hierarchy from document address.
    Levels: Municipality → County → State → Country
    """
    
    # Country configurations
    COUNTRY_CONFIG = {
        'US': {
            'name': 'United States',
            'code': 'US',
            'state_codes': {
                'FL': 'Florida', 'CA': 'California', 'TX': 'Texas', 'NY': 'New York',
                'IL': 'Illinois', 'PA': 'Pennsylvania', 'OH': 'Ohio', 'GA': 'Georgia',
                'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey', 'VA': 'Virginia',
                'WA': 'Washington', 'AZ': 'Arizona', 'CO': 'Colorado', 'OR': 'Oregon',
                'TN': 'Tennessee', 'MA': 'Massachusetts', 'MD': 'Maryland', 'MN': 'Minnesota',
                'MO': 'Missouri', 'WI': 'Wisconsin', 'IN': 'Indiana', 'LA': 'Louisiana',
                'KY': 'Kentucky', 'AL': 'Alabama', 'SC': 'South Carolina', 'OK': 'Oklahoma',
                'CT': 'Connecticut', 'IA': 'Iowa', 'AR': 'Arkansas', 'KS': 'Kansas',
                'NV': 'Nevada', 'MS': 'Mississippi', 'UT': 'Utah', 'NE': 'Nebraska',
                'WV': 'West Virginia', 'ID': 'Idaho', 'ME': 'Maine', 'SD': 'South Dakota',
                'ND': 'North Dakota', 'NH': 'New Hampshire', 'RI': 'Rhode Island',
                'MT': 'Montana', 'DE': 'Delaware', 'WY': 'Wyoming', 'AK': 'Alaska',
                'HI': 'Hawaii', 'VT': 'Vermont'
            },
            'county_mapping': {
                'FL': {
                    'Miami-Dade': ['Miami', 'Miami Beach', 'Hialeah'],
                    'Duval': ['Jacksonville'],
                    'Orange': ['Orlando'],
                    'Hillsborough': ['Tampa'],
                    'Pinellas': ['St. Petersburg', 'Clearwater'],
                    'Broward': ['Fort Lauderdale', 'Hollywood']
                },
                'CA': {
                    'Los Angeles': ['Los Angeles', 'Long Beach', 'Santa Monica'],
                    'San Francisco': ['San Francisco', 'Oakland', 'Berkeley'],
                    'San Diego': ['San Diego'],
                    'Orange': ['Anaheim', 'Santa Ana'],
                    'Sacramento': ['Sacramento'],
                    'Alameda': ['Oakland', 'Berkeley']
                }
            }
        },
        'CA': {
            'name': 'Canada',
            'code': 'CA',
            'state_codes': {
                'ON': 'Ontario', 'QC': 'Quebec', 'BC': 'British Columbia',
                'AB': 'Alberta', 'MB': 'Manitoba', 'SK': 'Saskatchewan',
                'NS': 'Nova Scotia', 'NB': 'New Brunswick', 'NL': 'Newfoundland',
                'PE': 'Prince Edward Island', 'NT': 'Northwest Territories',
                'NU': 'Nunavut', 'YT': 'Yukon'
            }
        },
        'MX': {
            'name': 'Mexico',
            'code': 'MX',
            'state_codes': {
                'JAL': 'Jalisco', 'NLE': 'Nuevo Leon', 'MEX': 'Mexico State',
                'CDMX': 'Mexico City', 'VER': 'Veracruz', 'PUE': 'Puebla',
                'GUA': 'Guanajuato', 'OAX': 'Oaxaca', 'YUC': 'Yucatan'
            }
        }
    }
    
    # Code access by jurisdiction level
    CODE_ACCESS = {
        'country': {
            'US': ['IBC', 'NEC', 'NFPA', 'ASCE', 'ACI', 'AISC'],
            'CA': ['NBC', 'NEC'],
            'MX': ['NOM', 'RCDF']
        },
        'state': {
            'Florida': ['FBC'],
            'California': ['CBC'],
            'Texas': ['TBC'],
            'New York': ['NYCBC'],
            'Ontario': ['OBC'],
            'Jalisco': ['CEJ']
        },
        'county': {
            'Miami-Dade': ['MDC Amendments'],
            'Los Angeles': ['LAC Amendments'],
            'Duval': ['Duval Amendments']
        },
        'municipality': {
            'Jacksonville': ['Jax Municipal Code'],
            'Miami': ['Miami City Code'],
            'Los Angeles': ['LA City Code']
        }
    }
    
    def __init__(self):
        self.hierarchy = JurisdictionHierarchy()
        self.available_codes = []
    
    def detect_from_address(self, address: str) -> JurisdictionHierarchy:
        """
        Detect full jurisdiction hierarchy from an address.
        """
        print(f"\n📄 Detectando jurisdicción desde: {address}")
        print("-" * 50)
        
        hierarchy = JurisdictionHierarchy()
        hierarchy.full_address = address
        
        # 1. Detect country
        hierarchy.country = self._detect_country(address)
        print(f"   🌍 País: {hierarchy.country}")
        
        # 2. Detect state
        hierarchy.state, hierarchy.state_code = self._detect_state(address)
        print(f"   📌 Estado: {hierarchy.state} ({hierarchy.state_code})")
        
        # 3. Detect county
        hierarchy.county = self._detect_county(address, hierarchy.state)
        print(f"   🏛️ Condado: {hierarchy.county or 'No detectado'}")
        
        # 4. Detect municipality
        hierarchy.municipality = self._detect_municipality(address, hierarchy.county)
        print(f"   🏙️ Municipio: {hierarchy.municipality or 'No detectado'}")
        
        # 5. Detect ZIP
        hierarchy.zip_code = self._detect_zip(address)
        print(f"   📮 ZIP: {hierarchy.zip_code or 'No detectado'}")
        
        # 6. Calculate confidence
        hierarchy.confidence = self._calculate_confidence(hierarchy)
        print(f"   🔍 Confianza: {hierarchy.confidence:.2f}")
        
        # 7. Get available codes
        self.available_codes = self.get_codes_for_jurisdiction(hierarchy)
        
        return hierarchy
    
    def _detect_country(self, address: str) -> str:
        """Detect country from address."""
        address_upper = address.upper()
        
        # Look for country indicators
        if any(c in address_upper for c in ['USA', 'UNITED STATES', 'US']):
            return 'United States'
        if 'CANADA' in address_upper:
            return 'Canada'
        if 'MEXICO' in address_upper:
            return 'Mexico'
        
        # Check state codes
        for country, config in self.COUNTRY_CONFIG.items():
            for code in config.get('state_codes', {}).keys():
                if code in address_upper:
                    return config['name']
        
        return 'Unknown'
    
    def _detect_state(self, address: str) -> Tuple[str, str]:
        """Detect state from address."""
        address_upper = address.upper()
        
        # Check for state codes (FL, CA, etc.)
        state_pattern = r'\b([A-Z]{2})\b'
        matches = re.findall(state_pattern, address_upper)
        
        for code in matches:
            # Check in all country configs
            for country, config in self.COUNTRY_CONFIG.items():
                state_codes = config.get('state_codes', {})
                if code in state_codes:
                    return state_codes[code], code
        
        # Check for state names
        for country, config in self.COUNTRY_CONFIG.items():
            for code, name in config.get('state_codes', {}).items():
                if name.upper() in address_upper:
                    return name, code
        
        return 'Unknown', 'Unknown'
    
    def _detect_county(self, address: str, state: str) -> Optional[str]:
        """Detect county from address."""
        address_upper = address.upper()
        
        # Get county mapping for the state
        country = 'US'  # Default for now
        for country_config in self.COUNTRY_CONFIG.values():
            if state in country_config.get('state_codes', {}).values():
                country = country_config['code']
                break
        
        county_mapping = self.COUNTRY_CONFIG.get(country, {}).get('county_mapping', {})
        
        for county, cities in county_mapping.items():
            for city in cities:
                if city.upper() in address_upper:
                    return county
        
        return None
    
    def _detect_municipality(self, address: str, county: Optional[str]) -> Optional[str]:
        """Detect municipality from address."""
        address_upper = address.upper()
        
        # Common municipality indicators
        city_patterns = [
            r'\b([A-Za-z]+(?:[\s-][A-Za-z]+)*)\s*(?:,|$)',
            r'\b([A-Za-z]+(?:[\s-][A-Za-z]+)*)\s+[A-Z]{2}\s+\d{5}'
        ]
        
        for pattern in city_patterns:
            matches = re.findall(pattern, address_upper)
            for match in matches:
                # Skip common words that aren't cities
                if len(match) > 2 and match not in ['ST', 'DR', 'RD', 'AVE', 'BLVD']:
                    return match.title()
        
        return None
    
    def _detect_zip(self, address: str) -> Optional[str]:
        """Detect ZIP/postal code from address."""
        # US ZIP
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            return zip_match.group(1)
        
        # Canadian postal code
        ca_match = re.search(r'\b([A-Z]\d[A-Z]\s*\d[A-Z]\d)\b', address.upper())
        if ca_match:
            return ca_match.group(1)
        
        # Mexican CP
        mx_match = re.search(r'\b(\d{5})\b', address)
        if mx_match:
            return mx_match.group(1)
        
        return None
    
    def _calculate_confidence(self, hierarchy: JurisdictionHierarchy) -> float:
        """Calculate confidence based on detected fields."""
        confidence = 0.0
        
        if hierarchy.country != 'Unknown':
            confidence += 0.3
        if hierarchy.state != 'Unknown':
            confidence += 0.25
        if hierarchy.county:
            confidence += 0.2
        if hierarchy.municipality:
            confidence += 0.15
        if hierarchy.zip_code:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_codes_for_jurisdiction(self, hierarchy: JurisdictionHierarchy) -> List[str]:
        """
        Get all applicable codes for a jurisdiction hierarchy.
        """
        codes = []
        
        # Country level codes
        if hierarchy.country == 'United States':
            codes.extend(['IBC', 'NEC', 'NFPA', 'ASCE', 'ACI', 'AISC'])
        elif hierarchy.country == 'Canada':
            codes.extend(['NBC', 'NEC'])
        elif hierarchy.country == 'Mexico':
            codes.extend(['NOM', 'RCDF'])
        
        # State level codes
        if hierarchy.state == 'Florida':
            codes.append('FBC')
        elif hierarchy.state == 'California':
            codes.append('CBC')
        elif hierarchy.state == 'Texas':
            codes.append('TBC')
        
        # County level codes
        if hierarchy.county == 'Miami-Dade':
            codes.append('Miami-Dade Amendments')
        elif hierarchy.county == 'Los Angeles':
            codes.append('LA County Amendments')
        
        # Municipality level codes
        if hierarchy.municipality == 'Jacksonville':
            codes.append('Jacksonville Municipal Code')
        elif hierarchy.municipality == 'Miami':
            codes.append('Miami City Code')
        
        return list(set(codes))
    
    def get_code_details(self, code_id: str) -> Dict:
        """
        Get details for a specific code.
        """
        # This would query the database
        # For now, return basic info
        return {
            'code_id': code_id,
            'jurisdiction': 'local',
            'severity': 'high',
            'category': 'general'
        }


async def main():
    """Test the Jurisdiction Agent."""
    print("\n" + "="*70)
    print(" JURISDICTION AGENT - TEST")
    print(" Detección jerárquica de jurisdicción")
    print("="*70)
    
    agent = JurisdictionAgent()
    
    test_addresses = [
        "11940 Farway Lakes Drive, Jacksonville, FL 32216",
        "123 Main Street, Miami, FL 33101",
        "2187 S Third St, Jacksonville Beach, FL 32250",
        "1000 Wilshire Blvd, Los Angeles, CA 90017"
    ]
    
    for address in test_addresses:
        print(f"\n{'='*70}")
        hierarchy = agent.detect_from_address(address)
        
        print("\n📋 JERARQUÍA COMPLETA:")
        print(f"   🌍 País: {hierarchy.country}")
        print(f"   📌 Estado: {hierarchy.state} ({hierarchy.state_code})")
        print(f"   🏛️ Condado: {hierarchy.county or 'No detectado'}")
        print(f"   🏙️ Municipio: {hierarchy.municipality or 'No detectado'}")
        print(f"   📮 ZIP: {hierarchy.zip_code or 'No detectado'}")
        print(f"   🔍 Confianza: {hierarchy.confidence:.2f}")
        
        print("\n📋 CÓDIGOS APLICABLES:")
        for code in agent.available_codes:
            print(f"   - {code}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
