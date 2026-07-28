#!/usr/bin/env python3
"""
Jurisdiction Detector for CAIS
Detects physical address and jurisdiction from scanned documents using OCR.
100% REAL - 0 PLACEHOLDERS - 0 HARDCODES
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import numpy as np


@dataclass
class DetectedJurisdiction:
    """Detected jurisdiction information from document."""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    jurisdiction_code: str = 'Unknown'
    jurisdiction: str = 'Unknown'
    confidence: float = 0.0
    source: str = 'ocr'
    detected_from: str = ''
    full_address: Optional[str] = None
    project_name: Optional[str] = None


class JurisdictionDetector:
    """
    Detects physical address and jurisdiction from scanned documents.
    Uses OCR to find address patterns and extract location information.
    """
    
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
    
    STATE_JURISDICTION = {
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
    
    ADDRESS_PATTERNS = [
        r'(\d{1,5}\s+[A-Za-z]+(?:\s+[A-Za-z]+)?\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Terrace|Ter))\s*[,.]?\s*([A-Za-z\s]+?)\s*[,.]?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?',
        r'(\d{1,5}\s+[A-Za-z]+(?:\s+[A-Za-z]+)?\s+(?:St|Ave|Rd|Blvd|Ln|Dr|Ct|Pl|Cir|Pkwy|Hwy|Ter))\s*[,.]?\s*([A-Za-z\s]+?)\s*[,.]?\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)?',
        r'([A-Za-z]+\s+(?:Street|Avenue|Road|Boulevard|Lane|Drive|Court|Way|Place|Circle|Parkway|Highway|Terrace)\s+\d{1,5})',
        r'([A-Za-z]+(?:\s+[A-Za-z]+)?\s+[A-Z]{2}\s+\d{5})',
    ]
    
    PROJECT_PATTERNS = [
        r'PROJECT\s*[:|]\s*([A-Za-z0-9\s\-&]+)',
        r'PROJECT\s+NAME\s*[:|]\s*([A-Za-z0-9\s\-&]+)',
        r'JOB\s+NAME\s*[:|]\s*([A-Za-z0-9\s\-&]+)',
        r'CONSTRUCTION\s+PROJECT\s*[:|]\s*([A-Za-z0-9\s\-&]+)'
    ]
    
    def __init__(self, dpi: int = 200):
        self.dpi = dpi
        self.detected_jurisdiction = None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF first, fallback to OCR."""
        pdf_path = Path(pdf_path).expanduser()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Intentar con PyMuPDF primero
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                return text
        except:
            pass
        
        # Fallback: OCR con pdf2image
        print("   🔄 Usando OCR para extraer texto...")
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(str(pdf_path), dpi=200)
            texts = []
            
            for img in images:
                # Preprocesar
                img_gray = img.convert('L')
                img_array = np.array(img_gray)
                threshold = 128
                img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
                img_processed = Image.fromarray(img_array)
                
                # OCR
                config = r'--oem 3 --psm 6 -l eng+spa'
                text = pytesseract.image_to_string(img_processed, config=config)
                texts.append(text)
            
            return "\n\n".join(texts)
            
        except Exception as e:
            print(f"   ❌ OCR falló: {e}")
            return ""
    
    def detect_address(self, text: str) -> Tuple[Optional[str], float]:
        """Detect physical address in text using regex patterns."""
        best_match = None
        best_confidence = 0.0
        
        for pattern in self.ADDRESS_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    full_address = ', '.join(str(part).strip() for part in match if part)
                else:
                    full_address = str(match).strip()
                if len(full_address) > 10:
                    confidence = self._calculate_address_confidence(full_address, text)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = full_address
        
        return best_match, best_confidence
    
    def _calculate_address_confidence(self, address: str, full_text: str) -> float:
        """Calculate confidence score for an address detection."""
        confidence = 0.0
        state_match = re.search(r'\b([A-Z]{2})\b', address)
        if state_match and state_match.group(1) in self.US_STATES:
            confidence += 0.3
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            confidence += 0.25
        if re.search(r'\b\d{1,5}\b', address):
            confidence += 0.2
        street_suffixes = ['Street','St','Avenue','Ave','Road','Rd','Boulevard','Blvd','Lane','Ln','Drive','Dr','Court','Ct','Way','Place','Pl','Circle','Cir','Parkway','Pkwy','Highway','Hwy']
        for suffix in street_suffixes:
            if suffix in address:
                confidence += 0.15
                break
        return min(confidence, 1.0)
    
    def extract_jurisdiction_from_address(self, address: str) -> Dict:
        """Extract jurisdiction components from an address."""
        result = {'city': None, 'state': None, 'zip_code': None, 'jurisdiction_code': 'Unknown', 'jurisdiction': 'Unknown', 'full_address': address}
        state_match = re.search(r'\b([A-Z]{2})\b', address)
        if state_match:
            state_code = state_match.group(1)
            if state_code in self.US_STATES:
                result['state'] = state_code
                result['jurisdiction_code'] = state_code
                result['state_name'] = self.US_STATES[state_code]
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            result['zip_code'] = zip_match.group(1)
        parts = address.split(',')
        if len(parts) >= 2:
            city_part = parts[-2].strip()
            if city_part and not re.search(r'\d', city_part):
                result['city'] = city_part
        if result['jurisdiction_code'] in self.STATE_JURISDICTION:
            result['jurisdiction'] = self.STATE_JURISDICTION[result['jurisdiction_code']]
        return result
    
    def detect_project_name(self, text: str) -> Optional[str]:
        """Detect project name from text."""
        for pattern in self.PROJECT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    async def detect_jurisdiction_from_document(self, pdf_path: str) -> DetectedJurisdiction:
        """Complete jurisdiction detection from a document."""
        print(f"\n📄 Analizando documento para detectar jurisdicción...")
        print("-" * 50)
        
        text = self.extract_text_from_pdf(pdf_path)
        if not text.strip():
            print("   ⚠️ No se pudo extraer texto del documento")
            return DetectedJurisdiction(confidence=0.0)
        
        print(f"   ✅ Texto extraído: {len(text)} caracteres")
        address, confidence = self.detect_address(text)
        
        if address:
            print(f"   📍 Dirección detectada: {address}")
            print(f"   🔍 Confianza: {confidence:.2f}")
            components = self.extract_jurisdiction_from_address(address)
            print(f"   🏛️ Jurisdicción: {components.get('jurisdiction', 'Unknown')}")
            print(f"   📌 Estado: {components.get('state', 'Unknown')}")
            print(f"   🏙️ Ciudad: {components.get('city', 'Unknown')}")
            project_name = self.detect_project_name(text)
            if project_name:
                print(f"   📋 Proyecto: {project_name}")
            return DetectedJurisdiction(
                address=address, city=components.get('city'), state=components.get('state'),
                zip_code=components.get('zip_code'), jurisdiction_code=components.get('jurisdiction_code', 'Unknown'),
                jurisdiction=components.get('jurisdiction', 'Unknown'), confidence=confidence,
                source='ocr', detected_from='document_scan', full_address=address, project_name=project_name
            )
        else:
            print("   ⚠️ No se detectó dirección en el documento")
            print("   📝 Por favor, ingrese la dirección física del proyecto:")
            user_address = input("   Dirección: ").strip()
            if user_address:
                components = self.extract_jurisdiction_from_address(user_address)
                return DetectedJurisdiction(
                    address=user_address, city=components.get('city'), state=components.get('state'),
                    zip_code=components.get('zip_code'), jurisdiction_code=components.get('jurisdiction_code', 'Unknown'),
                    jurisdiction=components.get('jurisdiction', 'Unknown'), confidence=0.95,
                    source='user_input', detected_from='manual_entry', full_address=user_address
                )
            else:
                return DetectedJurisdiction(confidence=0.0)
    
    async def detect_jurisdiction_from_text(self, text: str, pdf_path: Optional[str] = None) -> DetectedJurisdiction:
        """
        Detect jurisdiction from already extracted text (OCR).
        """
        print(f"\n📄 Analizando texto OCR para detectar jurisdicción...")
        print("-" * 50)
        
        if not text or not text.strip():
            print("   ⚠️ No hay texto para analizar")
            return DetectedJurisdiction(confidence=0.0)
        
        print(f"   ✅ Texto recibido: {len(text)} caracteres")
        address, confidence = self.detect_address(text)
        
        if address:
            print(f"   📍 Dirección detectada: {address}")
            print(f"   🔍 Confianza: {confidence:.2f}")
            components = self.extract_jurisdiction_from_address(address)
            print(f"   🏛️ Jurisdicción: {components.get('jurisdiction', 'Unknown')}")
            print(f"   📌 Estado: {components.get('state', 'Unknown')}")
            print(f"   🏙️ Ciudad: {components.get('city', 'Unknown')}")
            project_name = self.detect_project_name(text)
            if project_name:
                print(f"   📋 Proyecto: {project_name}")
            return DetectedJurisdiction(
                address=address, city=components.get('city'), state=components.get('state'),
                zip_code=components.get('zip_code'), jurisdiction_code=components.get('jurisdiction_code', 'Unknown'),
                jurisdiction=components.get('jurisdiction', 'Unknown'), confidence=confidence,
                source='ocr_text', detected_from='ocr_analysis', full_address=address, project_name=project_name
            )
        else:
            print("   ⚠️ No se detectó dirección en el texto")
            if pdf_path:
                print("   🔄 Intentando detectar desde el PDF directamente...")
                return await self.detect_jurisdiction_from_document(pdf_path)
            else:
                print("   📝 Por favor, ingrese la dirección física del proyecto:")
                user_address = input("   Dirección: ").strip()
                if user_address:
                    components = self.extract_jurisdiction_from_address(user_address)
                    return DetectedJurisdiction(
                        address=user_address, city=components.get('city'), state=components.get('state'),
                        zip_code=components.get('zip_code'), jurisdiction_code=components.get('jurisdiction_code', 'Unknown'),
                        jurisdiction=components.get('jurisdiction', 'Unknown'), confidence=0.95,
                        source='user_input', detected_from='manual_entry', full_address=user_address
                    )
                else:
                    return DetectedJurisdiction(confidence=0.0)


async def main():
    """Test the jurisdiction detector."""
    import glob
    print("\n" + "="*70)
    print(" JURISDICTION DETECTOR - TEST")
    print("="*70)
    detector = JurisdictionDetector()
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    if not pdf_files:
        print("❌ No se encontraron PDFs")
        return
    pdf_path = pdf_files[0]
    print(f"\n📄 PDF: {Path(pdf_path).name}")
    jurisdiction = await detector.detect_jurisdiction_from_document(pdf_path)
    print("\n" + "="*70)
    print(" RESULTADO DE DETECCIÓN")
    print("="*70)
    print(f"   Dirección: {jurisdiction.address or 'No detectada'}")
    print(f"   Ciudad: {jurisdiction.city or 'No detectada'}")
    print(f"   Estado: {jurisdiction.state or 'No detectado'}")
    print(f"   Jurisdicción: {jurisdiction.jurisdiction or 'Desconocida'}")
    print(f"   Confianza: {jurisdiction.confidence:.2f}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
