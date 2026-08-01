"""
Jurisdiction Orchestrator Agent - Identifies jurisdiction from address
and retrieves applicable building codes, safety regulations, and laws.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 4.2
"""

import logging
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.db.models import Base

logger = logging.getLogger(__name__)


class JurisdictionOrchestrator(BaseAgent):
    """
    Jurisdiction Orchestrator Agent.

    Responsibilities:
    1. Identify jurisdiction from physical address
    2. Retrieve building codes, safety regulations, and laws
    3. Transmit code information to CodeMatcher
    """

    # US State mapping
    US_STATES = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
        'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota',
        'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
        'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
        'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
        'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming'
    }

    # Major cities with known jurisdictions
    MAJOR_CITIES = {
        'new york': {'jurisdiction': 'NYC', 'state': 'NY', 'code_set': 'NYC'},
        'los angeles': {'jurisdiction': 'LA', 'state': 'CA', 'code_set': 'LABC'},
        'chicago': {'jurisdiction': 'Chicago', 'state': 'IL', 'code_set': 'CBC'},
        'miami': {'jurisdiction': 'Miami-Dade', 'state': 'FL', 'code_set': 'FBC'},
        'houston': {'jurisdiction': 'Houston', 'state': 'TX', 'code_set': 'TBC'},
        'san francisco': {'jurisdiction': 'SF', 'state': 'CA', 'code_set': 'SFBC'},
        'seattle': {'jurisdiction': 'Seattle', 'state': 'WA', 'code_set': 'SBC'},
        'denver': {'jurisdiction': 'Denver', 'state': 'CO', 'code_set': 'DBC'},
        'boston': {'jurisdiction': 'Boston', 'state': 'MA', 'code_set': 'MBC'},
        'washington': {'jurisdiction': 'DC', 'state': 'DC', 'code_set': 'DCBC'},
        'philadelphia': {'jurisdiction': 'Philadelphia', 'state': 'PA', 'code_set': 'PBC'},
        'dallas': {'jurisdiction': 'Dallas', 'state': 'TX', 'code_set': 'TBC'},
        'san diego': {'jurisdiction': 'San Diego', 'state': 'CA', 'code_set': 'SDBC'},
        'san jose': {'jurisdiction': 'San Jose', 'state': 'CA', 'code_set': 'SJBC'},
        'austin': {'jurisdiction': 'Austin', 'state': 'TX', 'code_set': 'TBC'},
        'jacksonville': {'jurisdiction': 'Jacksonville', 'state': 'FL', 'code_set': 'FBC'},
        'fort worth': {'jurisdiction': 'Fort Worth', 'state': 'TX', 'code_set': 'TBC'},
        'columbus': {'jurisdiction': 'Columbus', 'state': 'OH', 'code_set': 'OBC'},
        'charlotte': {'jurisdiction': 'Charlotte', 'state': 'NC', 'code_set': 'NCBC'},
        'indianapolis': {'jurisdiction': 'Indianapolis', 'state': 'IN', 'code_set': 'IBC'},
        'las vegas': {'jurisdiction': 'Las Vegas', 'state': 'NV', 'code_set': 'NVBC'},
        'portland': {'jurisdiction': 'Portland', 'state': 'OR', 'code_set': 'OBC'},
        'detroit': {'jurisdiction': 'Detroit', 'state': 'MI', 'code_set': 'MIBC'},
        'memphis': {'jurisdiction': 'Memphis', 'state': 'TN', 'code_set': 'TNBC'},
        'oklahoma city': {'jurisdiction': 'Oklahoma City', 'state': 'OK', 'code_set': 'OKBC'},
    }

    def __init__(self, db_session=None):
        super().__init__("JurisdictionOrchestrator", "jurisdiction")
        self.db_session = db_session

    def analyze(self, document) -> Dict[str, Any]:
        """
        Implementation of the abstract analyze method from BaseAgent.

        Args:
            document: Document object containing address information

        Returns:
            dict: Jurisdiction information
        """
        # Extract address from document
        address = None
        if hasattr(document, 'address'):
            address = document.address
        elif hasattr(document, 'file_path'):
            # Try to extract from file path or content
            address = self._extract_address_from_document(document)

        if not address:
            logger.warning("No address found in document for jurisdiction detection")
            return {
                'jurisdiction': 'Unknown',
                'state': 'Unknown',
                'code_set': 'IBC',
                'confidence': 0.0,
                'detected_from': 'None'
            }

        return self.identify_jurisdiction(address)

    def _extract_address_from_document(self, document) -> Optional[str]:
        """
        Extract address from document content if available.
        """
        if hasattr(document, 'extracted_text') and document.extracted_text:
            text = document.extracted_text
            # Simple address pattern matching
            patterns = [
                r'(?:address|location|site|project)\s*:?\s*([^\n]{5,100})',
                r'(\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln|court|ct|way|circle|cir|place|pl|terrace|ter)\.?\s*[A-Z]{2}\s*\d{5})',
                r'(\d{1,5}\s+[A-Za-z]+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s*,\s*[A-Z]{2}\s*\d{5})',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None

    def identify_jurisdiction(self, address: str) -> Dict[str, Any]:
        """
        Identify jurisdiction from a physical address.

        Args:
            address: Physical address string

        Returns:
            dict: Jurisdiction information
        """
        logger.info(f"Identifying jurisdiction for address: {address}")

        if not address or len(address.strip()) < 5:
            return {
                'jurisdiction': 'Unknown',
                'state': 'Unknown',
                'code_set': 'IBC',
                'confidence': 0.0,
                'detected_from': address
            }

        address_lower = address.lower()

        # Check major cities first
        for city, data in self.MAJOR_CITIES.items():
            if city in address_lower:
                logger.info(f"Identified city: {city} -> {data['jurisdiction']}")
                return {
                    'jurisdiction': data['jurisdiction'],
                    'state': data['state'],
                    'code_set': data['code_set'],
                    'confidence': 0.9,
                    'detected_from': city,
                    'city': city
                }

        # Check US state abbreviations
        state_abbr_match = re.search(r'\b([A-Z]{2})\b', address)
        if state_abbr_match:
            abbr = state_abbr_match.group(1).upper()
            if abbr in self.US_STATES:
                logger.info(f"Identified state: {abbr} -> {self.US_STATES[abbr]}")
                return {
                    'jurisdiction': self.US_STATES[abbr],
                    'state': abbr,
                    'code_set': f'US-{abbr}',
                    'confidence': 0.7,
                    'detected_from': abbr
                }

        # Check for state names
        for abbr, name in self.US_STATES.items():
            if name.lower() in address_lower:
                logger.info(f"Identified state name: {name}")
                return {
                    'jurisdiction': name,
                    'state': abbr,
                    'code_set': f'US-{abbr}',
                    'confidence': 0.6,
                    'detected_from': name
                }

        # Fallback: return IBC as default
        logger.warning(f"No jurisdiction identified for address: {address}")
        return {
            'jurisdiction': 'Unknown',
            'state': 'Unknown',
            'code_set': 'IBC',
            'confidence': 0.0,
            'detected_from': address
        }

    def get_applicable_codes(self, jurisdiction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get applicable building codes for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction information

        Returns:
            List of applicable codes
        """
        logger.info(f"Getting applicable codes for {jurisdiction}")

        # Base IBC codes (always applicable)
        codes = self._get_ibc_codes()

        # Add state-specific codes if available
        state = jurisdiction.get('state', '')
        if state and state in self.US_STATES:
            state_codes = self._get_state_codes(state)
            codes.extend(state_codes)

        # Add local codes if available
        local_code_set = jurisdiction.get('code_set', '')
        if local_code_set and local_code_set != 'IBC':
            local_codes = self._get_local_codes(local_code_set)
            codes.extend(local_codes)

        return codes

    def _get_ibc_codes(self) -> List[Dict[str, Any]]:
        """Get base IBC codes."""
        return [
            {
                'code_type': 'IBC',
                'section': '1005.3.1',
                'title': 'Means of Egress Door Width',
                'description': 'Minimum door width for means of egress shall be 32 inches (813 mm).',
                'severity': 'Critical'
            },
            {
                'code_type': 'IBC',
                'section': '1007',
                'title': 'Means of Egress for Fire Safety',
                'description': 'Means of egress shall be designed and maintained to provide a safe path of travel.',
                'severity': 'Critical'
            },
            {
                'code_type': 'IBC',
                'section': '1004',
                'title': 'Occupant Load',
                'description': 'Occupant load shall be determined based on the use of the space.',
                'severity': 'High'
            },
            {
                'code_type': 'IBC',
                'section': '1604.4',
                'title': 'Structural Integrity',
                'description': 'Structures shall be designed to resist all applicable loads.',
                'severity': 'High'
            },
            {
                'code_type': 'IBC',
                'section': '1803.5',
                'title': 'Foundation Requirements',
                'description': 'Foundations shall be designed and constructed to support the structure.',
                'severity': 'High'
            },
            {
                'code_type': 'IBC',
                'section': '1006.2.1',
                'title': 'Egress Width Requirements',
                'description': 'Minimum egress width shall be 32 inches (813 mm).',
                'severity': 'Critical'
            }
        ]

    def _get_state_codes(self, state: str) -> List[Dict[str, Any]]:
        """Get state-specific codes."""
        state_map = {
            'CA': [
                {
                    'code_type': 'STATE',
                    'section': 'CA-001',
                    'title': 'California Building Code',
                    'description': 'California specific building code requirements.',
                    'severity': 'High'
                }
            ],
            'FL': [
                {
                    'code_type': 'STATE',
                    'section': 'FL-001',
                    'title': 'Florida Building Code',
                    'description': 'Florida specific building code requirements including hurricane resistance.',
                    'severity': 'High'
                }
            ],
            'NY': [
                {
                    'code_type': 'STATE',
                    'section': 'NY-001',
                    'title': 'New York Building Code',
                    'description': 'New York specific building code requirements.',
                    'severity': 'High'
                }
            ],
            'TX': [
                {
                    'code_type': 'STATE',
                    'section': 'TX-001',
                    'title': 'Texas Building Code',
                    'description': 'Texas specific building code requirements.',
                    'severity': 'High'
                }
            ]
        }
        return state_map.get(state, [])

    def _get_local_codes(self, code_set: str) -> List[Dict[str, Any]]:
        """Get local-specific codes."""
        local_map = {
            'NYC': [
                {
                    'code_type': 'LOCAL',
                    'section': 'NYC-001',
                    'title': 'NYC Building Code',
                    'description': 'New York City specific building code requirements.',
                    'severity': 'High'
                }
            ],
            'LABC': [
                {
                    'code_type': 'LOCAL',
                    'section': 'LA-001',
                    'title': 'Los Angeles Building Code',
                    'description': 'Los Angeles specific building code requirements including seismic.',
                    'severity': 'High'
                }
            ],
            'CBC': [
                {
                    'code_type': 'LOCAL',
                    'section': 'CHI-001',
                    'title': 'Chicago Building Code',
                    'description': 'Chicago specific building code requirements.',
                    'severity': 'High'
                }
            ]
        }
        return local_map.get(code_set, [])

    def get_safety_regulations(self, jurisdiction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get safety regulations for a jurisdiction."""
        # NFPA regulations (always applicable)
        regulations = [
            {
                'code_type': 'NFPA',
                'section': 'NFPA 101',
                'title': 'Life Safety Code',
                'description': 'Requirements for life safety in buildings.',
                'severity': 'Critical'
            },
            {
                'code_type': 'NFPA',
                'section': 'NFPA 13',
                'title': 'Sprinkler Systems',
                'description': 'Requirements for fire sprinkler systems.',
                'severity': 'High'
            },
            {
                'code_type': 'NFPA',
                'section': 'NFPA 70',
                'title': 'National Electrical Code',
                'description': 'Requirements for electrical systems.',
                'severity': 'High'
            }
        ]

        # OSHA regulations (always applicable)
        regulations.extend([
            {
                'code_type': 'OSHA',
                'section': '1926.20',
                'title': 'Safety and Health Programs',
                'description': 'Requirements for safety and health programs.',
                'severity': 'High'
            },
            {
                'code_type': 'OSHA',
                'section': '1926.21',
                'title': 'Safety Training',
                'description': 'Requirements for safety training.',
                'severity': 'Medium'
            }
        ])

        return regulations

    def get_construction_laws(self, jurisdiction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get construction laws for a jurisdiction."""
        # ADA regulations (always applicable)
        laws = [
            {
                'code_type': 'ADA',
                'section': 'ADA-001',
                'title': 'Americans with Disabilities Act',
                'description': 'Requirements for accessibility.',
                'severity': 'Critical'
            }
        ]

        # Federal laws
        laws.extend([
            {
                'code_type': 'FEDERAL',
                'section': 'FED-001',
                'title': 'Federal Construction Regulations',
                'description': 'Federal requirements for construction projects.',
                'severity': 'High'
            }
        ])

        return laws
