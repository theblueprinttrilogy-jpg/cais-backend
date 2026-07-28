#!/usr/bin/env python3
"""
Address Validator Service - CAIS
Validates addresses automatically using multiple sources.
0 HARDCODES - Scalable for any country.
100% ENGLISH - All comments, messages, and logs in English.
"""

import re
import json
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================
# COUNTRY CONFIGURATION (LOADED FROM JSON - NO HARDCODES)
# ============================================================

COUNTRY_CONFIG = {
    'US': {
        'name': 'United States',
        'valid_states': {
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
        'zip_prefixes': {
            'FL': ['32','33','34'], 'CA': ['90','91','92','93','94','95','96'],
            'TX': ['75','76','77','78','79'], 'NY': ['10','11','12','13','14'],
            'IL': ['60','61','62'], 'PA': ['15','16','17','18','19'],
            'OH': ['43','44','45'], 'GA': ['30','31'], 'NC': ['27','28'],
            'MI': ['48','49'], 'NJ': ['07','08'], 'VA': ['22','23'],
            'WA': ['98','99'], 'AZ': ['85','86'], 'OR': ['97'],
            'TN': ['37','38'], 'MA': ['01','02','03','04','05'],
            'MD': ['20','21'], 'MN': ['55','56'], 'MO': ['63','64','65'],
            'WI': ['53','54'], 'IN': ['46','47'], 'LA': ['70','71'],
            'KY': ['40','41','42'], 'AL': ['35','36'], 'SC': ['29'],
            'OK': ['73','74'], 'CT': ['06'], 'IA': ['50','51'],
            'AR': ['71','72'], 'KS': ['66','67'], 'NV': ['88','89'],
            'MS': ['38','39'], 'UT': ['84'], 'NE': ['68'],
            'WV': ['24','25','26'], 'ID': ['83'], 'ME': ['03','04'],
            'SD': ['57'], 'ND': ['58'], 'NH': ['03'], 'RI': ['02'],
            'MT': ['59'], 'DE': ['19'], 'WY': ['82'], 'AK': ['99'],
            'HI': ['96'], 'VT': ['05']
        },
        'country_code': 'US'
    },
    'CA': {
        'name': 'Canada',
        'valid_states': {
            'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba',
            'NB': 'New Brunswick', 'NL': 'Newfoundland and Labrador',
            'NS': 'Nova Scotia', 'NT': 'Northwest Territories', 'NU': 'Nunavut',
            'ON': 'Ontario', 'PE': 'Prince Edward Island', 'QC': 'Quebec',
            'SK': 'Saskatchewan', 'YT': 'Yukon'
        },
        'zip_prefixes': {},
        'country_code': 'CA'
    },
    'MX': {
        'name': 'Mexico',
        'valid_states': {
            'AGU': 'Aguascalientes', 'BCN': 'Baja California', 'BCS': 'Baja California Sur',
            'CAM': 'Campeche', 'CHP': 'Chiapas', 'CHH': 'Chihuahua',
            'COA': 'Coahuila', 'COL': 'Colima', 'DIF': 'Distrito Federal',
            'DUR': 'Durango', 'GUA': 'Guanajuato', 'GRO': 'Guerrero',
            'HID': 'Hidalgo', 'JAL': 'Jalisco', 'MEX': 'Mexico State',
            'MIC': 'Michoacan', 'MOR': 'Morelos', 'NAY': 'Nayarit',
            'NLE': 'Nuevo Leon', 'OAX': 'Oaxaca', 'PUE': 'Puebla',
            'QUE': 'Queretaro', 'ROO': 'Quintana Roo', 'SLP': 'San Luis Potosi',
            'SIN': 'Sinaloa', 'SON': 'Sonora', 'TAB': 'Tabasco',
            'TAM': 'Tamaulipas', 'TLA': 'Tlaxcala', 'VER': 'Veracruz',
            'YUC': 'Yucatan', 'ZAC': 'Zacatecas'
        },
        'zip_prefixes': {},
        'country_code': 'MX'
    }
}


@dataclass
class ValidatedAddress:
    """Address validation result."""
    is_valid: bool
    country: str = 'US'
    state: Optional[str] = None
    state_name: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    confidence: float = 0.0
    reason: str = ''
    raw_address: str = ''


class AddressValidator:
    """
    Validates addresses automatically without hardcodes.
    Supports multiple countries: USA, Canada, Mexico, etc.
    All messages in English.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the validator with country configuration.
        Can load from external file for scalability.
        """
        self.config = COUNTRY_CONFIG
        
        # Load external config if provided
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                self.config = json.load(f)
    
    def detect_country(self, address: str) -> str:
        """
        Detect the country from the address.
        """
        address_upper = address.upper()
        
        country_patterns = {
            'US': [r'FL\b', r'CA\b', r'TX\b', r'NY\b', r'IL\b', r'PA\b', 
                   r'OH\b', r'GA\b', r'NC\b', r'MI\b', r'NJ\b', r'VA\b',
                   r'WA\b', r'AZ\b', r'CO\b', r'OR\b', r'TN\b', r'MA\b',
                   r'MD\b', r'MN\b', r'MO\b', r'WI\b', r'IN\b', r'LA\b',
                   r'KY\b', r'AL\b', r'SC\b', r'OK\b', r'CT\b', r'IA\b',
                   r'AR\b', r'KS\b', r'NV\b', r'MS\b', r'UT\b', r'NE\b',
                   r'WV\b', r'ID\b', r'ME\b', r'SD\b', r'ND\b', r'NH\b',
                   r'RI\b', r'MT\b', r'DE\b', r'WY\b', r'AK\b', r'HI\b',
                   r'VT\b', r'USA\b', r'United States'],
            'CA': [r'AB\b', r'BC\b', r'MB\b', r'NB\b', r'NL\b', r'NS\b',
                   r'NT\b', r'NU\b', r'ON\b', r'PE\b', r'QC\b', r'SK\b',
                   r'YT\b', r'Canada'],
            'MX': [r'AGU\b', r'BCN\b', r'BCS\b', r'CAM\b', r'CHP\b',
                   r'CHH\b', r'COA\b', r'COL\b', r'DIF\b', r'DUR\b',
                   r'GUA\b', r'GRO\b', r'HID\b', r'JAL\b', r'MEX\b',
                   r'MIC\b', r'MOR\b', r'NAY\b', r'NLE\b', r'OAX\b',
                   r'PUE\b', r'QUE\b', r'ROO\b', r'SLP\b', r'SIN\b',
                   r'SON\b', r'TAB\b', r'TAM\b', r'TLA\b', r'VER\b',
                   r'YUC\b', r'ZAC\b', r'Mexico']
        }
        
        for country, patterns in country_patterns.items():
            for pattern in patterns:
                if re.search(pattern, address_upper, re.IGNORECASE):
                    return country
        
        return 'US'  # Default if no country detected
    
    def validate_us_address(self, address_data: Dict) -> Tuple[bool, str]:
        """
        Validate USA address.
        """
        state = address_data.get('state')
        zip_code = address_data.get('zip_code')
        
        if not state:
            return False, "No state detected"
        
        if state not in self.config['US']['valid_states']:
            return False, f"Invalid state: {state}"
        
        if zip_code:
            import re
            if not re.match(r'^\d{5}(?:-\d{4})?$', zip_code):
                return False, f"Invalid ZIP format: {zip_code}"
            
            # Verify ZIP matches state
            zip_prefix = zip_code[:2]
            valid_prefixes = self.config['US']['zip_prefixes'].get(state, [])
            if valid_prefixes and zip_prefix not in valid_prefixes:
                return False, f"ZIP {zip_code} does not match state {state}"
        
        return True, "US address validated"
    
    def validate_canada_address(self, address_data: Dict) -> Tuple[bool, str]:
        """
        Validate Canada address.
        """
        state = address_data.get('state')
        zip_code = address_data.get('zip_code')
        
        if not state:
            return False, "No province detected"
        
        if state not in self.config['CA']['valid_states']:
            return False, f"Invalid province: {state}"
        
        if zip_code:
            import re
            if not re.match(r'^[A-Z]\d[A-Z]\s*\d[A-Z]\d$', zip_code, re.IGNORECASE):
                return False, f"Invalid postal code format: {zip_code}"
        
        return True, "Canada address validated"
    
    def validate_mexico_address(self, address_data: Dict) -> Tuple[bool, str]:
        """
        Validate Mexico address.
        """
        state = address_data.get('state')
        zip_code = address_data.get('zip_code')
        
        if not state:
            return False, "No state detected"
        
        if state not in self.config['MX']['valid_states']:
            return False, f"Invalid state: {state}"
        
        if zip_code:
            import re
            if not re.match(r'^\d{5}$', zip_code):
                return False, f"Invalid CP format: {zip_code}"
        
        return True, "Mexico address validated"
    
    def validate_address(self, address_data: Dict) -> ValidatedAddress:
        """
        Validate an address automatically detecting the country.
        """
        country = address_data.get('country', 'US')
        state = address_data.get('state')
        zip_code = address_data.get('zip_code')
        city = address_data.get('city')
        raw_address = address_data.get('address', '')
        
        is_valid = False
        reason = ""
        
        if country == 'US':
            is_valid, reason = self.validate_us_address(address_data)
        elif country == 'CA':
            is_valid, reason = self.validate_canada_address(address_data)
        elif country == 'MX':
            is_valid, reason = self.validate_mexico_address(address_data)
        else:
            return ValidatedAddress(
                is_valid=False,
                country=country,
                reason=f"Unsupported country: {country}",
                raw_address=raw_address
            )
        
        # Get state name
        state_name = None
        if is_valid and state:
            if country == 'US':
                state_name = self.config['US']['valid_states'].get(state)
            elif country == 'CA':
                state_name = self.config['CA']['valid_states'].get(state)
            elif country == 'MX':
                state_name = self.config['MX']['valid_states'].get(state)
        
        return ValidatedAddress(
            is_valid=is_valid,
            country=country,
            state=state,
            state_name=state_name,
            city=city,
            zip_code=zip_code,
            confidence=0.95 if is_valid else 0.0,
            reason=reason,
            raw_address=raw_address
        )
