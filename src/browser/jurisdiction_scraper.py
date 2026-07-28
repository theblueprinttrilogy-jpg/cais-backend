#!/usr/bin/env python3
"""
Jurisdiction Scraper - CAIS
Browser-based scraper for jurisdiction data from Wikipedia and other sources.
100% ENGLISH - All comments, messages, and logs in English.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Browser, Page, Response


@dataclass
class JurisdictionData:
    """Complete jurisdiction data from web sources."""
    country: str
    state: str
    state_code: str
    capital: Optional[str] = None
    population: Optional[int] = None
    area: Optional[float] = None
    official_language: Optional[str] = None
    building_codes: List[str] = field(default_factory=list)
    safety_regulations: List[str] = field(default_factory=list)
    construction_laws: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class JurisdictionScraper:
    """
    Browser-based scraper for jurisdiction data.
    Uses Playwright to fetch data from Wikipedia and other sources.
    """
    
    # Source URLs for jurisdiction data
    SOURCES = {
        'us_states': 'https://en.wikipedia.org/wiki/List_of_states_and_territories_of_the_United_States',
        'us_counties': 'https://en.wikipedia.org/wiki/List_of_United_States_counties_and_county_equivalents',
        'canada_provinces': 'https://en.wikipedia.org/wiki/Provinces_and_territories_of_Canada',
        'mexico_states': 'https://en.wikipedia.org/wiki/Administrative_divisions_of_Mexico',
        'building_codes': 'https://en.wikipedia.org/wiki/Building_code',
        'building_codes_us': 'https://en.wikipedia.org/wiki/Building_code#United_States'
    }
    
    # Known building codes by jurisdiction
    KNOWN_CODES = {
        'United States': {
            'building_codes': ['IBC', 'IRC', 'IECC', 'IGCC'],
            'safety_regulations': ['NFPA', 'OSHA', 'ASCE'],
            'construction_laws': ['NEC', 'IPC', 'IMC', 'IFC']
        },
        'Florida': {
            'building_codes': ['FBC', 'FEC'],
            'safety_regulations': ['Florida Fire Prevention Code'],
            'construction_laws': ['Florida Building Code']
        },
        'California': {
            'building_codes': ['CBC', 'CRC'],
            'safety_regulations': ['California Fire Code'],
            'construction_laws': ['California Building Code']
        },
        'Canada': {
            'building_codes': ['NBC', 'NEC'],
            'safety_regulations': ['Canadian Fire Code'],
            'construction_laws': ['National Building Code']
        },
        'Mexico': {
            'building_codes': ['NOM', 'RCDF'],
            'safety_regulations': ['Normas Oficiales Mexicanas'],
            'construction_laws': ['Reglamento de Construcciones']
        }
    }
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize the jurisdiction scraper.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.cache_dir = Path('./cache/jurisdictions')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def __aenter__(self):
        """Enter async context."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Fetch a page with retries.
        
        Args:
            url: URL to fetch
            retries: Number of retries on failure
        
        Returns:
            HTML content or None if failed
        """
        for attempt in range(retries):
            try:
                print(f"   🌐 Fetching: {url} (attempt {attempt + 1}/{retries})")
                response = await self.page.goto(url, timeout=self.timeout)
                
                if response and response.status == 200:
                    content = await self.page.content()
                    return content
                else:
                    print(f"      ⚠️ Status: {response.status if response else 'No response'}")
                    
            except Exception as e:
                print(f"      ⚠️ Error: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    async def scrape_us_states(self) -> List[Dict]:
        """
        Scrape US states from Wikipedia.
        """
        print("\n📄 Scraping US states from Wikipedia...")
        
        content = await self._fetch_page(self.SOURCES['us_states'])
        if not content:
            return []
        
        states = []
        
        # Find the states table
        table_pattern = r'<table[^>]*class="wikitable[^"]*"[^>]*>.*?</table>'
        tables = re.findall(table_pattern, content, re.DOTALL)
        
        if tables:
            # Parse first table (states)
            table = tables[0]
            # Extract rows
            rows = re.findall(r'<tr[^>]*>.*?</tr>', table, re.DOTALL)
            
            for row in rows[1:]:  # Skip header
                # Extract columns
                cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cols) >= 4:
                    # Clean text
                    state_name = re.sub(r'<[^>]+>', '', cols[0]).strip()
                    state_code = re.sub(r'<[^>]+>', '', cols[1]).strip()
                    capital = re.sub(r'<[^>]+>', '', cols[2]).strip()
                    
                    if state_name and state_code:
                        states.append({
                            'name': state_name,
                            'code': state_code,
                            'capital': capital,
                            'source': self.SOURCES['us_states']
                        })
                        print(f"   ✅ {state_name} ({state_code})")
        
        return states
    
    async def get_jurisdiction_data(self, jurisdiction: str) -> JurisdictionData:
        """
        Get comprehensive data for a jurisdiction.
        
        Args:
            jurisdiction: Jurisdiction name (e.g., 'Florida', 'California')
        
        Returns:
            JurisdictionData object
        """
        print(f"\n🔍 Fetching data for: {jurisdiction}")
        
        # Check cache first
        cache_file = self.cache_dir / f"{jurisdiction.lower().replace(' ', '_')}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    print(f"   📁 Cache hit: {jurisdiction}")
                    return JurisdictionData(**data)
            except:
                pass
        
        # Build from known data
        known = self.KNOWN_CODES.get(jurisdiction, {})
        
        # Scrape Wikipedia for additional info
        search_url = f"https://en.wikipedia.org/wiki/{jurisdiction.replace(' ', '_')}"
        content = await self._fetch_page(search_url)
        
        # Parse basic info
        data = JurisdictionData(
            country='United States' if jurisdiction in self.KNOWN_CODES else 'Unknown',
            state=jurisdiction,
            state_code=self._extract_state_code(content, jurisdiction),
            capital=self._extract_capital(content),
            population=self._extract_population(content),
            area=self._extract_area(content),
            official_language=self._extract_language(content),
            building_codes=known.get('building_codes', []),
            safety_regulations=known.get('safety_regulations', []),
            construction_laws=known.get('construction_laws', []),
            source_urls=[search_url]
        )
        
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(data.__dict__, f, indent=2)
        
        return data
    
    def _extract_state_code(self, content: Optional[str], state: str) -> str:
        """Extract state code from content."""
        if not content:
            # Try common state codes
            us_states = {
                'Florida': 'FL', 'California': 'CA', 'Texas': 'TX', 'New York': 'NY',
                'Illinois': 'IL', 'Pennsylvania': 'PA', 'Ohio': 'OH', 'Georgia': 'GA',
                'North Carolina': 'NC', 'Michigan': 'MI', 'New Jersey': 'NJ', 'Virginia': 'VA'
            }
            return us_states.get(state, 'Unknown')
        
        # Look for state code in the page
        code_pattern = r'<td[^>]*>([A-Z]{2})</td>'
        codes = re.findall(code_pattern, content)
        
        # Try to find the code near the state name
        for i, code in enumerate(codes):
            if code.upper() in state.upper():
                return code
        
        return 'Unknown'
    
    def _extract_capital(self, content: Optional[str]) -> Optional[str]:
        """Extract capital from content."""
        if not content:
            return None
        
        capital_patterns = [
            r'<th[^>]*>Capital</th>[^<]*<td[^>]*>([^<]+)</td>',
            r'Capital[^>]*:?\s*([A-Za-z\s]+)',
        ]
        
        for pattern in capital_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return re.sub(r'<[^>]+>', '', match.group(1)).strip()
        
        return None
    
    def _extract_population(self, content: Optional[str]) -> Optional[int]:
        """Extract population from content."""
        if not content:
            return None
        
        patterns = [
            r'Population[^>]*:?\s*([\d,]+)',
            r'<th[^>]*>Population</th>[^<]*<td[^>]*>([\d,]+)</td>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(',', ''))
        
        return None
    
    def _extract_area(self, content: Optional[str]) -> Optional[float]:
        """Extract area from content."""
        if not content:
            return None
        
        patterns = [
            r'Area[^>]*:?\s*([\d,]+)\s*(?:km²|sq mi)',
            r'<th[^>]*>Area</th>[^<]*<td[^>]*>([\d,]+)</td>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        
        return None
    
    def _extract_language(self, content: Optional[str]) -> Optional[str]:
        """Extract official language from content."""
        if not content:
            return None
        
        patterns = [
            r'Official language[^>]*:?\s*([A-Za-z\s]+)',
            r'<th[^>]*>Official languages?</th>[^<]*<td[^>]*>([^<]+)</td>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return re.sub(r'<[^>]+>', '', match.group(1)).strip()
        
        return None
    
    async def get_all_us_states(self) -> List[Dict]:
        """Get all US states with data."""
        return await self.scrape_us_states()
    
    async def get_jurisdiction_by_zip(self, zip_code: str) -> Optional[JurisdictionData]:
        """
        Get jurisdiction from ZIP code.
        """
        # This would use a ZIP code API or database
        # For now, return based on known ZIP ranges
        zip_prefix = zip_code[:3] if zip_code else '000'
        
        # US ZIP prefixes by state
        state_zip_map = {
            'FL': ['32', '33', '34'],
            'CA': ['90', '91', '92', '93', '94', '95', '96'],
            'TX': ['75', '76', '77', '78', '79'],
            'NY': ['10', '11', '12', '13', '14'],
            'IL': ['60', '61', '62'],
            'PA': ['15', '16', '17', '18', '19'],
            'OH': ['43', '44', '45'],
            'GA': ['30', '31'],
            'NC': ['27', '28'],
            'MI': ['48', '49'],
            'NJ': ['07', '08'],
            'VA': ['22', '23'],
            'WA': ['98', '99'],
            'AZ': ['85', '86'],
            'OR': ['97'],
            'TN': ['37', '38'],
            'MA': ['01', '02', '03', '04', '05'],
            'MD': ['20', '21'],
            'MN': ['55', '56'],
            'MO': ['63', '64', '65'],
            'WI': ['53', '54'],
            'IN': ['46', '47'],
            'LA': ['70', '71'],
            'KY': ['40', '41', '42'],
            'AL': ['35', '36'],
            'SC': ['29'],
            'OK': ['73', '74'],
            'CT': ['06'],
            'IA': ['50', '51'],
            'AR': ['71', '72'],
            'KS': ['66', '67'],
            'NV': ['88', '89'],
            'MS': ['38', '39'],
            'UT': ['84'],
            'NE': ['68'],
            'WV': ['24', '25', '26'],
            'ID': ['83'],
            'ME': ['03', '04'],
            'SD': ['57'],
            'ND': ['58'],
            'NH': ['03'],
            'RI': ['02'],
            'MT': ['59'],
            'DE': ['19'],
            'WY': ['82'],
            'AK': ['99'],
            'HI': ['96'],
            'VT': ['05']
        }
        
        for state, prefixes in state_zip_map.items():
            if zip_prefix in prefixes:
                state_name = {
                    'FL': 'Florida', 'CA': 'California', 'TX': 'Texas', 'NY': 'New York',
                    'IL': 'Illinois', 'PA': 'Pennsylvania', 'OH': 'Ohio', 'GA': 'Georgia',
                    'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey', 'VA': 'Virginia',
                    'WA': 'Washington', 'AZ': 'Arizona', 'OR': 'Oregon', 'TN': 'Tennessee',
                    'MA': 'Massachusetts', 'MD': 'Maryland', 'MN': 'Minnesota', 'MO': 'Missouri',
                    'WI': 'Wisconsin', 'IN': 'Indiana', 'LA': 'Louisiana', 'KY': 'Kentucky',
                    'AL': 'Alabama', 'SC': 'South Carolina', 'OK': 'Oklahoma', 'CT': 'Connecticut',
                    'IA': 'Iowa', 'AR': 'Arkansas', 'KS': 'Kansas', 'NV': 'Nevada',
                    'MS': 'Mississippi', 'UT': 'Utah', 'NE': 'Nebraska', 'WV': 'West Virginia',
                    'ID': 'Idaho', 'ME': 'Maine', 'SD': 'South Dakota', 'ND': 'North Dakota',
                    'NH': 'New Hampshire', 'RI': 'Rhode Island', 'MT': 'Montana', 'DE': 'Delaware',
                    'WY': 'Wyoming', 'AK': 'Alaska', 'HI': 'Hawaii', 'VT': 'Vermont'
                }.get(state, 'Unknown')
                
                return await self.get_jurisdiction_data(state_name)
        
        return None


async def main():
    """Test the Jurisdiction Scraper."""
    print("\n" + "="*70)
    print(" JURISDICTION SCRAPER - TEST")
    print(" Browser-based jurisdiction data collection")
    print("="*70)
    
    async with JurisdictionScraper(headless=False) as scraper:
        # Get US states
        states = await scraper.get_all_us_states()
        print(f"\n📊 Found {len(states)} US states")
        
        # Get specific state data
        for state_name in ['Florida', 'California', 'Texas']:
            data = await scraper.get_jurisdiction_data(state_name)
            print(f"\n📋 {state_name}:")
            print(f"   Code: {data.state_code}")
            print(f"   Capital: {data.capital or 'Unknown'}")
            print(f"   Population: {data.population or 'Unknown'}")
            print(f"   Building Codes: {', '.join(data.building_codes) if data.building_codes else 'None'}")


if __name__ == "__main__":
    asyncio.run(main())
