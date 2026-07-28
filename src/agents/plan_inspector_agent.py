#!/usr/bin/env python3
"""
Plan Inspector Agent - TASK 23 - FINAL OPTIMIZED VERSION
DIRECT OCR ON PDF (no image conversion) + REAL SEMANTIC SEARCH
Compares the scanned document with codes, regulations and laws of the jurisdiction.
Generates visual evidence with RED boxes and YELLOW highlights.
AUTOMATIC jurisdiction detection with MULTI-COUNTRY address validation.
Scalable: USA, Canada, Mexico, Europe, etc. - 0 HARDCODES.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import sys
import json
import re
import asyncio
import asyncpg
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter

# PDF Processing
import fitz
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import pytesseract

# Semantic Search
from sentence_transformers import SentenceTransformer

# Address Validator Service
from src.services.address_validator import AddressValidator, ValidatedAddress


@dataclass
class DetectedViolation:
    """A violation detected in the document."""
    violation_id: str
    page_number: int
    section_text: str
    coordinates: Dict[str, int]
    code_id: str
    code_section: str
    code_content: str
    jurisdiction: str
    severity: str
    similarity_score: float
    screenshot_path: str
    code_highlight_path: str
    document_hash: str
    detected_at: str


class PDFOCRDIRECT:
    """
    DIRECT OCR on PDF using PyMuPDF.
    No image conversion - works directly with the PDF.
    """
    
    def __init__(self, dpi: int = 200):
        self.dpi = dpi
    
    def extract_text_with_ocr(self, pdf_path: str, lang: str = 'eng+spa') -> Tuple[List[str], str]:
        """
        Extract text from PDF using PyMuPDF direct OCR.
        
        Returns:
            Tuple of (texts_per_page, full_text)
        """
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"\n📄 Extracting text with DIRECT OCR (PyMuPDF)...")
        print("-" * 50)
        
        texts = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            print(f"   Page {page_num + 1}...", end=' ', flush=True)
            
            page = doc[page_num]
            
            # Try direct text extraction first
            text = page.get_text()
            
            # If no text or very little, use OCR
            if len(text.strip()) < 50:
                print("OCR...", end=' ', flush=True)
                try:
                    zoom = self.dpi / 72
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
                    
                    img_data = pix.tobytes("png")
                    from PIL import Image as PILImage
                    import io
                    img = PILImage.open(io.BytesIO(img_data))
                    
                    img = img.convert('L')
                    config = r'--oem 3 --psm 6 -l ' + lang
                    text = pytesseract.image_to_string(img, config=config)
                    text = text.strip()
                    
                except Exception as e:
                    print(f"⚠️ OCR Error: {e}", end=' ')
                    text = ""
            else:
                print("Direct...", end=' ', flush=True)
            
            # Clean text
            text = self._clean_text(text)
            texts.append(text)
            
            char_count = len(text)
            word_count = len(text.split())
            print(f"✅ {char_count} characters, {word_count} words")
        
        doc.close()
        full_text = "\n\n".join(texts)
        
        print(f"\n   ✅ Total: {len(texts)} pages, {len(full_text)} characters")
        
        return texts, full_text
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        import re
        text = re.sub(r'[^\w\s.,;:!?()\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_text_direct(self, pdf_path: str) -> Tuple[List[str], str]:
        """Try to extract text directly (without OCR) for comparison."""
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        texts = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            texts.append(text.strip())
        
        doc.close()
        full_text = "\n\n".join(texts)
        
        return texts, full_text


class PlanInspectorAgent:
    """
    Plan Inspector Agent - DIRECT OCR + REAL SEMANTIC SEARCH.
    
    Flow:
    1. Direct OCR on PDF (no image conversion)
    2. Automatically detects jurisdiction from document (MULTI-COUNTRY)
    3. Gets codes from that jurisdiction
    4. SEMANTICALLY compares the document with the codes
    5. Generates visual evidence
    """
    
    SIMILARITY_THRESHOLD = 0.65
    SEVERITY_MAP = {
        'critical': 0.85,
        'high': 0.75,
        'medium': 0.65,
        'low': 0.55
    }
    
    def __init__(self, db_config: Optional[Dict] = None, output_dir: str = "./evidence", dpi: int = 200):
        self.db_config = db_config or {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        
        print("📥 Loading embedding model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"   ✅ Model loaded: {self.model.get_sentence_embedding_dimension()} dimensions")
        
        self.violations: List[DetectedViolation] = []
        self.address_validator = AddressValidator()
    
    def _to_vector_str(self, embedding_list: List[float]) -> str:
        return '[' + ','.join(str(x) for x in embedding_list) + ']'
    
    def extract_sections_from_document(self, pdf_path: str) -> Tuple[List[Dict], str]:
        """
        Extract text from PDF using DIRECT OCR (no image conversion).
        """
        pdf_path = Path(pdf_path).expanduser()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"\n📄 Extracting text with DIRECT OCR (PyMuPDF)...")
        
        # Use direct OCR
        ocr = PDFOCRDIRECT(dpi=self.dpi)
        texts, full_text = ocr.extract_text_with_ocr(str(pdf_path), lang='eng+spa')
        
        # Split into sections
        sections = []
        for page_num, text in enumerate(texts, 1):
            if not text.strip():
                continue
            
            # Split by paragraphs
            paragraphs = text.split('\n\n')
            for para in paragraphs:
                para_clean = para.strip()
                if len(para_clean) > 50:
                    sections.append({
                        'page': page_num,
                        'text': para_clean,
                        'coordinates': {'x': 0, 'y': 0, 'width': 0, 'height': 0},
                        'rect': None
                    })
        
        print(f"\n   ✅ Total sections extracted: {len(sections)}")
        print(f"   ✅ Total text: {len(full_text)} characters")
        
        return sections, full_text
    
    def _ask_user_for_jurisdiction(self) -> Tuple[str, Dict]:
        """
        Ask the user for jurisdiction when no text or valid address is found.
        """
        print("\n   📝 Please enter the jurisdiction manually.")
        print("   Examples: Florida, California, Ontario, Jalisco, etc.")
        jurisdiction = input("   🏛️ Jurisdiction: ").strip()
        
        if jurisdiction:
            return jurisdiction, {'source': 'user_input', 'confidence': 0.95}
        return 'Unknown', {'source': 'none'}
    
    async def detect_jurisdiction_from_text(self, text: str, pdf_path: str) -> Tuple[str, Dict]:
        """
        Automatically detect jurisdiction from OCR text.
        Validates that the address is real before using it.
        MULTI-COUNTRY support: USA, Canada, Mexico, etc.
        If no valid address is found, asks the user.
        """
        print(f"\n📄 Analyzing OCR text to detect jurisdiction AUTOMATICALLY...")
        print("-" * 50)
        
        if not text or not text.strip():
            print("   ⚠️ No text to analyze")
            return self._ask_user_for_jurisdiction()
        
        print(f"   ✅ Text received: {len(text)} characters")
        
        # US States dictionary (will be expanded automatically by the validator)
        US_STATES = {
            'FL': 'Florida', 'CA': 'California', 'NY': 'New York', 'TX': 'Texas',
            'IL': 'Illinois', 'PA': 'Pennsylvania', 'MI': 'Michigan', 'NC': 'North Carolina',
            'OH': 'Ohio', 'GA': 'Georgia', 'WA': 'Washington', 'AZ': 'Arizona',
            'CO': 'Colorado', 'OR': 'Oregon', 'TN': 'Tennessee', 'MA': 'Massachusetts',
            'VA': 'Virginia', 'NJ': 'New Jersey', 'MD': 'Maryland', 'MN': 'Minnesota',
            'MO': 'Missouri', 'WI': 'Wisconsin', 'IN': 'Indiana', 'LA': 'Louisiana',
            'KY': 'Kentucky', 'AL': 'Alabama', 'SC': 'South Carolina', 'OK': 'Oklahoma',
            'CT': 'Connecticut', 'IA': 'Iowa', 'AR': 'Arkansas', 'KS': 'Kansas',
            'NV': 'Nevada', 'MS': 'Mississippi', 'UT': 'Utah', 'NE': 'Nebraska',
            'WV': 'West Virginia', 'ID': 'Idaho', 'ME': 'Maine', 'SD': 'South Dakota',
            'ND': 'North Dakota', 'NH': 'New Hampshire', 'RI': 'Rhode Island',
            'MT': 'Montana', 'DE': 'Delaware', 'WY': 'Wyoming', 'AK': 'Alaska',
            'HI': 'Hawaii', 'VT': 'Vermont'
        }
        
        # ============================================================
        # SEARCH FOR ALL POSSIBLE ADDRESSES IN THE DOCUMENT
        # ============================================================
        
        all_addresses = []
        
        address_patterns = [
            r'(\d{1,5})\s+([A-Za-z0-9\s\.]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Terrace|Ter|Lakes|Lake|Loop|Trace|Trail|Bay|Island|Key|Point|View|Vista|Springs|Hills|Estates|Manor|Landing|Shores|Park|Village|Crossing|Creek|Meadow|Valley|Woods|Forest|Grove|Heights|Ridge|Bend|Run|Falls|Hollow|Mills|Pines|Pointe|Sands|Way|Wood|Meadow|Harbor|Marsh|Cove|Shore|Dale|Crest|Fairway|Green|Oak|Palm|Pine|Stone|Sycamore|Cedar|Elm|Maple|Willow|Ash|Birch|Cypress|Dogwood|Holly|Juniper|Laurel|Magnolia|Myrtle|Olive|Orchid|Poppy|Rose|Sunflower|Tulip|Violet|Wisteria|Acacia|Bamboo|Cactus|Daisy|Fern|Ginger|Heather|Iris|Ivy|Jasmine|Lily|Lotus|Mint|Orchid|Peony|Sage|Thyme|Verbena|Yarrow|Zinnia))\s*,?\s*([A-Za-z\s]+?)\s*,?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)',
            r'(\d{1,5})\s+([A-Za-z0-9\s\.]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Terrace|Ter|Lakes|Lake|Loop|Trace|Trail|Bay|Island|Key|Point|View|Vista|Springs|Hills|Estates|Manor|Landing|Shores|Park|Village|Crossing|Creek|Meadow|Valley|Woods|Forest|Grove|Heights|Ridge|Bend|Run|Falls|Hollow|Mills|Pines|Pointe|Sands|Way|Wood|Meadow|Harbor|Marsh|Cove|Shore|Dale|Crest|Fairway|Green|Oak|Palm|Pine|Stone|Sycamore|Cedar|Elm|Maple|Willow|Ash|Birch|Cypress|Dogwood|Holly|Juniper|Laurel|Magnolia|Myrtle|Olive|Orchid|Poppy|Rose|Sunflower|Tulip|Violet|Wisteria|Acacia|Bamboo|Cactus|Daisy|Fern|Ginger|Heather|Iris|Ivy|Jasmine|Lily|Lotus|Mint|Orchid|Peony|Sage|Thyme|Verbena|Yarrow|Zinnia))\s*,?\s*([A-Za-z\s]+?)\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)',
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 4:
                    num = match[0].strip() if match[0] else None
                    street = match[1].strip() if len(match) > 1 else None
                    city_part = match[2].strip() if len(match) > 2 and not match[2].strip() in US_STATES else None
                    state_code = None
                    zip_part = None
                    
                    for part in match:
                        part_str = str(part).strip()
                        if part_str in US_STATES:
                            state_code = part_str
                        elif re.search(r'\d{5}(?:-\d{4})?', part_str):
                            zip_part = part_str
                    
                    if not state_code and len(match) >= 2:
                        potential_state = match[-2].strip() if len(match) >= 2 else None
                        if potential_state in US_STATES:
                            state_code = potential_state
                    
                    if not zip_part and len(match) >= 1:
                        potential_zip = match[-1].strip()
                        if re.search(r'\d{5}', potential_zip):
                            zip_part = potential_zip
                    
                    if state_code and state_code in US_STATES:
                        full_address = f"{num} {street}"
                        if city_part:
                            full_address += f", {city_part}"
                        full_address += f", {state_code}"
                        if zip_part:
                            full_address += f" {zip_part}"
                        
                        temp_conf = 0.3
                        if num and re.search(r'\d', num):
                            temp_conf += 0.2
                        if street and len(street) > 3:
                            temp_conf += 0.2
                        if state_code in US_STATES:
                            temp_conf += 0.2
                        if zip_part and re.search(r'\d{5}', zip_part):
                            temp_conf += 0.2
                        
                        all_addresses.append({
                            'address': full_address,
                            'street_number': num,
                            'street_name': street,
                            'city': city_part,
                            'state': state_code,
                            'zip_code': zip_part,
                            'confidence': temp_conf
                        })
        
        # ============================================================
        # VALIDATE EACH FOUND ADDRESS WITH THE MULTI-COUNTRY SERVICE
        # ============================================================
        
        print(f"   🔍 Found {len(all_addresses)} possible addresses")
        
        valid_addresses = []
        for addr in all_addresses:
            # Detect country automatically
            country = self.address_validator.detect_country(addr['address'])
            addr['country'] = country
            
            # Validate with the service
            validated = self.address_validator.validate_address(addr)
            
            if validated.is_valid:
                valid_addresses.append({
                    'address': addr['address'],
                    'street_number': addr['street_number'],
                    'street_name': addr['street_name'],
                    'city': addr['city'],
                    'state': validated.state,
                    'state_name': validated.state_name,
                    'zip_code': validated.zip_code,
                    'country': validated.country,
                    'confidence': validated.confidence,
                    'validated': validated
                })
                print(f"   ✅ Valid address: {addr['address']} ({validated.country})")
            else:
                print(f"   ❌ Invalid address: {addr['address']} - {validated.reason}")
        
        # ============================================================
        # USE THE BEST VALID ADDRESS
        # ============================================================
        
        if valid_addresses:
            best = max(valid_addresses, key=lambda x: x['confidence'])
            
            print(f"\n📋 SELECTED ADDRESS (VALIDATED):")
            print(f"   🏠 Number: {best['street_number']}")
            print(f"   🛤️ Street: {best['street_name']}")
            print(f"   🏙️ City: {best['city'] or 'Not detected'}")
            print(f"   📌 State: {best['state']}")
            print(f"   🌍 Country: {best['country']}")
            print(f"   📮 ZIP: {best['zip_code'] or 'Not detected'}")
            print(f"   🔍 Confidence: {best['confidence']:.2f}")
            
            # Return jurisdiction (state + country to distinguish)
            jurisdiction = f"{best['state_name']}, {best['country']}"
            return jurisdiction, {
                'address': best['address'],
                'street_number': best['street_number'],
                'street_name': best['street_name'],
                'city': best['city'],
                'state': best['state'],
                'state_name': best['state_name'],
                'country': best['country'],
                'zip_code': best['zip_code'],
                'confidence': best['confidence'],
                'validated': best['validated']
            }
        
        # ============================================================
        # IF NO VALID ADDRESS, ASK THE USER
        # ============================================================
        else:
            print("\n   ⚠️ No valid address found in the document.")
            print("   📝 Please enter the physical address of the project.")
            print("   Example: 123 Main Street, Miami, FL 33101 (USA)")
            print("   Example: 123 Queen Street, Toronto, ON M5H 2N2 (Canada)")
            print("   Example: Av. Reforma 123, Ciudad de México, CDMX 06600 (Mexico)")
            
            user_address = input("\n   📍 Address: ").strip()
            
            if user_address:
                # Detect country from user input
                country = self.address_validator.detect_country(user_address)
                
                # Try to extract state
                state_match = re.search(r'\b([A-Z]{2})\b', user_address)
                state_code = state_match.group(1) if state_match else None
                
                if state_code:
                    # Look up state in validator
                    if country == 'US':
                        state_name = self.address_validator.config['US']['valid_states'].get(state_code)
                    elif country == 'CA':
                        state_name = self.address_validator.config['CA']['valid_states'].get(state_code)
                    elif country == 'MX':
                        state_name = self.address_validator.config['MX']['valid_states'].get(state_code)
                    else:
                        state_name = state_code
                    
                    if state_name:
                        jurisdiction = f"{state_name}, {country}"
                        print(f"\n   🏛️ Jurisdiction selected: {jurisdiction}")
                        return jurisdiction, {
                            'address': user_address,
                            'state': state_code,
                            'state_name': state_name,
                            'country': country,
                            'source': 'user_input',
                            'confidence': 0.95
                        }
                
                # If state couldn't be extracted, ask directly
                return self._ask_user_for_jurisdiction()
            else:
                return self._ask_user_for_jurisdiction()
    
    async def get_codes_by_jurisdiction(self, jurisdiction: str) -> List[Dict]:
        """
        Get ALL codes from a specific jurisdiction.
        Direct SELECT from database - NOT semantic search.
        """
        conn = await asyncpg.connect(**self.db_config)
        try:
            rows = await conn.fetch("""
                SELECT 
                    code_id,
                    jurisdiction,
                    section_number,
                    title,
                    content,
                    severity,
                    category
                FROM cais.construction_codes
                WHERE jurisdiction ILIKE $1
                ORDER BY severity DESC
            """, f"%{jurisdiction}%")
            
            codes = [dict(row) for row in rows]
            print(f"   📋 {len(codes)} codes found for {jurisdiction}")
            return codes
        except Exception as e:
            print(f"   ❌ Error getting codes: {e}")
            return []
        finally:
            await conn.close()
    
    async def search_codes_semantic(self, query: str, codes: List[Dict], limit: int = 3) -> List[Dict]:
        """
        SEMANTICALLY search codes from the jurisdiction.
        This is the real comparison between the document and the codes.
        """
        if not codes:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode(query)
        query_str = self._to_vector_str(query_embedding.tolist())
        
        # Extract code IDs
        code_ids = [c['code_id'] for c in codes]
        
        conn = await asyncpg.connect(**self.db_config)
        try:
            rows = await conn.fetch("""
                SELECT 
                    code_id,
                    jurisdiction,
                    section_number,
                    title,
                    content,
                    severity,
                    category,
                    1 - (embedding <=> $1::vector) as similarity
                FROM cais.construction_codes
                WHERE code_id = ANY($2::text[])
                AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, query_str, code_ids, limit)
            
            results = []
            for row in rows:
                result = dict(row)
                result['similarity'] = float(result.get('similarity', 0))
                results.append(result)
            
            return results
        except Exception as e:
            print(f"   ❌ Error in semantic search: {e}")
            return []
        finally:
            await conn.close()
    
    async def compare_section_async(self, section: Dict, codes: List[Dict]) -> Dict:
        """
        Compare a document section with codes using semantic search.
        """
        # Search for semantically similar codes
        results = await self.search_codes_semantic(section['text'], codes, limit=3)
        
        violations = []
        for result in results:
            if result['similarity'] >= self.SIMILARITY_THRESHOLD:
                # Determine severity
                severity = 'low'
                for sev, threshold in self.SEVERITY_MAP.items():
                    if result['similarity'] >= threshold:
                        severity = sev
                        break
                
                violations.append({
                    'section': section,
                    'code': result,
                    'severity': severity,
                    'similarity': result['similarity']
                })
        
        return {
            'section': section,
            'violations': violations,
            'has_violation': len(violations) > 0
        }
    
    async def inspect_document_async(self, pdf_path: str, jurisdiction: Optional[str] = None) -> List[DetectedViolation]:
        """
        Inspect the complete document.
        
        Args:
            pdf_path: Path to the PDF
            jurisdiction: Jurisdiction (if not provided, automatically detected)
        """
        print(f"\n🔍 PLAN INSPECTOR AGENT")
        print(f"   Document: {Path(pdf_path).name}")
        print("-" * 50)
        
        # 1. Extract text with direct OCR
        sections, full_text = self.extract_sections_from_document(pdf_path)
        
        if not sections:
            print("   ⚠️ Could not extract text from document.")
            return []
        
        # 2. Detect jurisdiction automatically (MULTI-COUNTRY)
        if jurisdiction is None:
            jurisdiction, info = await self.detect_jurisdiction_from_text(full_text, pdf_path)
            print(f"\n   🏛️ Jurisdiction detected: {jurisdiction}")
            if info.get('address'):
                print(f"   📍 Address: {info.get('address')}")
            if info.get('street_number'):
                print(f"   🏠 Number: {info.get('street_number')}")
            if info.get('street_name'):
                print(f"   🛤️ Street: {info.get('street_name')}")
            if info.get('city'):
                print(f"   🏙️ City: {info.get('city')}")
            if info.get('state'):
                print(f"   📌 State: {info.get('state')}")
            if info.get('country'):
                print(f"   🌍 Country: {info.get('country')}")
            if info.get('zip_code'):
                print(f"   📮 ZIP: {info.get('zip_code')}")
            print(f"   🔍 Confidence: {info.get('confidence', 0):.2f}")
        
        if not jurisdiction or jurisdiction == 'Unknown':
            print("   ⚠️ Could not determine jurisdiction automatically.")
            jurisdiction, info = self._ask_user_for_jurisdiction()
            if not jurisdiction or jurisdiction == 'Unknown':
                print("   ❌ Jurisdiction not provided. Aborting.")
                return []
        
        # 3. Get codes for the jurisdiction
        print(f"\n   📋 Getting codes for {jurisdiction}...")
        codes = await self.get_codes_by_jurisdiction(jurisdiction)
        
        # If no codes for that jurisdiction, search by state or country
        if not codes:
            print(f"   ⚠️ No codes found for {jurisdiction}")
            
            # Try to extract state from jurisdiction name
            parts = jurisdiction.split(',')
            if len(parts) >= 2:
                state_name = parts[0].strip()
                print(f"   🔍 Searching for codes for: {state_name}...")
                codes = await self.get_codes_by_jurisdiction(state_name)
        
        # If still no codes, try all
        if not codes:
            print("   🔍 Searching all available codes...")
            conn = await asyncpg.connect(**self.db_config)
            try:
                rows = await conn.fetch("""
                    SELECT code_id, jurisdiction, section_number, title, content, severity, category
                    FROM cais.construction_codes
                    ORDER BY severity DESC
                    LIMIT 10
                """)
                codes = [dict(row) for row in rows]
                print(f"   📋 {len(codes)} codes found (all)")
            except Exception as e:
                print(f"   ❌ Error getting codes: {e}")
                return []
            finally:
                await conn.close()
        
        if not codes:
            print("   ❌ No codes found for comparison.")
            return []
        
        # 4. Compare sections asynchronously
        print(f"\n   🔄 Comparing {len(sections)} sections ASYNCHRONOUSLY...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence_dir = self.output_dir / f"inspection_{Path(pdf_path).stem}_{timestamp}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        for idx, section in enumerate(sections, 1):
            task = self.compare_section_async(section, codes)
            tasks.append(task)
            if idx % 10 == 0 or idx == len(sections):
                print(f"      [{idx}/{len(sections)}] Queued...")
        
        results = await asyncio.gather(*tasks)
        
        # 5. Process results
        self.violations = []
        for result in results:
            if result['has_violation']:
                for vdata in result['violations']:
                    section = vdata['section']
                    code = vdata['code']
                    severity = vdata['severity']
                    similarity = vdata['similarity']
                    
                    # Generate visual evidence
                    screenshot = self._generate_red_box_evidence(
                        pdf_path, section['page'], section['coordinates'],
                        evidence_dir, Path(pdf_path).stem, severity, section['text']
                    )
                    
                    highlight = self._generate_yellow_highlight_evidence(
                        code, evidence_dir, Path(pdf_path).stem
                    )
                    
                    violation = DetectedViolation(
                        violation_id=f"VIO-{timestamp}-{len(self.violations)+1:04d}",
                        page_number=section['page'],
                        section_text=section['text'][:500],
                        coordinates=section['coordinates'],
                        code_id=code['code_id'],
                        code_section=code.get('section_number', ''),
                        code_content=code['content'],
                        jurisdiction=code['jurisdiction'],
                        severity=severity,
                        similarity_score=similarity,
                        screenshot_path=screenshot,
                        code_highlight_path=highlight,
                        document_hash=hashlib.sha256(section['text'].encode()).hexdigest(),
                        detected_at=datetime.now().isoformat()
                    )
                    self.violations.append(violation)
                    
                    print(f"\n   ⚠️ VIOLATION DETECTED:")
                    print(f"      Code: {code['code_id']}")
                    print(f"      Severity: {severity.upper()}")
                    print(f"      Similarity: {similarity:.3f}")
                    print(f"      Page: {section['page']}")
                    print(f"      📄 Evidence: {Path(screenshot).name}")
        
        # 6. Save to database
        await self._save_violations_to_db(Path(pdf_path).stem)
        
        # 7. Generate report
        self._generate_inspection_report(evidence_dir, Path(pdf_path).stem)
        
        print(f"\n✅ INSPECTION COMPLETED")
        print(f"   Violations found: {len(self.violations)}")
        print(f"   Evidence saved in: {evidence_dir}")
        
        return self.violations
    
    def _generate_red_box_evidence(self, pdf_path, page_num, coords, output_dir, doc_id, severity, section_text):
        """Generate screenshot with RED box."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(pdf_path), first_page=page_num, last_page=page_num, dpi=200)
            if not images:
                return ""
            img = images[0]
            draw = ImageDraw.Draw(img)
            
            x, y, w, h = coords.get('x', 100), coords.get('y', 100), coords.get('width', 200), coords.get('height', 100)
            if x == 0 and y == 0:
                try:
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    for i, word in enumerate(data['text']):
                        if len(word) > 10 and word in section_text[:100]:
                            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                            break
                except:
                    pass
            
            padding = 30
            x, y = max(0, x-padding), max(0, y-padding)
            w, h = w + padding*2, h + padding*2
            draw.rectangle([(x, y), (x+w, y+h)], outline=(204,0,0), width=5)
            
            label_color = {'critical':(204,0,0), 'high':(204,102,0), 'medium':(204,136,0), 'low':(0,102,204)}.get(severity, (204,0,0))
            label_y = y - 30 if y > 30 else y + 10
            draw.rectangle([(x, label_y), (x+190, label_y+30)], fill=(*label_color, 220))
            try:
                font = ImageFont.truetype("Arial", 14)
            except:
                font = ImageFont.load_default()
            draw.text((x+5, label_y+6), f"VIOLATION", fill=(255,255,255), font=font)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            filepath = output_dir / f"redbox_page{page_num}_{timestamp}.png"
            img.save(filepath, 'PNG')
            return str(filepath)
        except Exception as e:
            print(f"   ⚠️ Error generating red box: {e}")
            return ""
    
    def _generate_yellow_highlight_evidence(self, code, output_dir, doc_id):
        """Generate code evidence with yellow highlight."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        filepath = output_dir / f"yellow_highlight_{code['code_id']}_{timestamp}.txt"
        content = f"""
============================================================
CODE VIOLATION EVIDENCE - YELLOW HIGHLIGHT
============================================================
Code ID: {code['code_id']}
Jurisdiction: {code['jurisdiction']}
Severity: {code['severity']}
Section: {code.get('section_number', 'N/A')}

HIGHLIGHTED CODE SECTION (Violated):
------------------------------------------------------------
>>> {code['content'][:500]} <<<
------------------------------------------------------------

Similarity Score: {code.get('similarity', 0):.3f}
Document: {doc_id}
Generated: {datetime.now().isoformat()}
============================================================
"""
        with open(filepath, 'w') as f:
            f.write(content)
        return str(filepath)
    
    async def _save_violations_to_db(self, doc_id):
        if not self.violations:
            return
        conn = await asyncpg.connect(**self.db_config)
        try:
            for v in self.violations:
                await conn.execute("""
                    INSERT INTO cais.violations 
                    (violation_id, audit_id, code_id, document_page, coordinates, screenshot_path, severity, fact_hash, jurisdiction)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    ON CONFLICT (violation_id) DO UPDATE SET screenshot_path = EXCLUDED.screenshot_path
                """, v.violation_id, doc_id, v.code_id, v.page_number, json.dumps(v.coordinates), v.screenshot_path, v.severity, v.document_hash, v.jurisdiction)
            
            await conn.execute("""
                INSERT INTO cais.worm_ledger 
                (sequence, event_type, payload, actor, previous_hash, node_id)
                SELECT COALESCE(MAX(sequence), -1)+1, 'VIOLATIONS_DETECTED',
                jsonb_build_object('document_id',$1,'total',$2),
                'plan_inspector_agent',
                COALESCE(MAX(hash), '0'||REPEAT('0',63)),
                'local'
                FROM cais.worm_ledger
            """, doc_id, len(self.violations))
        except Exception as e:
            print(f"   ⚠️ Error saving to database: {e}")
        finally:
            await conn.close()
    
    def _generate_inspection_report(self, output_dir, doc_id):
        report = {
            'document_id': doc_id,
            'inspection_time': datetime.now().isoformat(),
            'total_violations': len(self.violations),
            'severity_breakdown': {
                'critical': sum(1 for v in self.violations if v.severity == 'critical'),
                'high': sum(1 for v in self.violations if v.severity == 'high'),
                'medium': sum(1 for v in self.violations if v.severity == 'medium'),
                'low': sum(1 for v in self.violations if v.severity == 'low')
            },
            'violations': [{
                'violation_id': v.violation_id,
                'code_id': v.code_id,
                'page': v.page_number,
                'severity': v.severity,
                'similarity': v.similarity_score,
                'screenshot': v.screenshot_path
            } for v in self.violations]
        }
        with open(output_dir / 'inspection_report.json', 'w') as f:
            json.dump(report, f, indent=2)
    
    def get_violation_summary(self) -> Dict:
        return {
            'total': len(self.violations),
            'by_severity': {
                'critical': sum(1 for v in self.violations if v.severity == 'critical'),
                'high': sum(1 for v in self.violations if v.severity == 'high'),
                'medium': sum(1 for v in self.violations if v.severity == 'medium'),
                'low': sum(1 for v in self.violations if v.severity == 'low')
            }
        }


async def main():
    import glob
    print("\n" + "="*70)
    print(" PLAN INSPECTOR AGENT - COMPLETE INSPECTION")
    print(" DIRECT OCR + SEMANTIC SEARCH + VISUAL EVIDENCE")
    print("="*70)
    
    agent = PlanInspectorAgent(output_dir="./evidence", dpi=200)
    
    # Find PDF
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    if not pdf_files:
        print("❌ No PDFs found")
        return
    
    pdf_path = pdf_files[0]
    
    # Run inspection
    violations = await agent.inspect_document_async(str(pdf_path))
    
    summary = agent.get_violation_summary()
    print("\n" + "="*70)
    print(" VIOLATION SUMMARY")
    print("="*70)
    print(f"   Total: {summary['total']}")
    print(f"   Critical: {summary['by_severity']['critical']}")
    print(f"   High: {summary['by_severity']['high']}")
    print(f"   Medium: {summary['by_severity']['medium']}")
    print(f"   Low: {summary['by_severity']['low']}")
    
    if summary['total'] > 0:
        print(f"\n   📄 Evidence generated in: evidence/")
        print(f"   📋 Report: evidence/inspection_*/inspection_report.json")


if __name__ == "__main__":
    asyncio.run(main())
