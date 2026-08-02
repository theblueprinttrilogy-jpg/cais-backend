"""
PlanInspector Agent - Visual Scanner for Construction Documents

This agent receives a PDF and runs OCR directly on the PDF at 200 DPI,
without converting to intermediate images. This preserves quality and accuracy.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 4.1
"""

import logging
import os
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import pdf2image
import pytesseract
from PIL import Image, ImageDraw
import cv2
import numpy as np

from app.agents.base_agent import BaseAgent
from app.db.models import Document, Violation

logger = logging.getLogger(__name__)


class PlanInspector(BaseAgent):
    """
    PlanInspector Agent - Visual Scanner with Direct PDF OCR

    Responsibilities:
    1. Run OCR directly on PDF at 200 DPI (no intermediate images)
    2. Scan each page for patterns using OCR text
    3. Detect numerical patterns (door widths, dimensions)
    4. Detect keywords (FIRE EXIT, EMERGENCY, DOOR, WIDTH, SAFETY, OCCUPANCY, CAPACITY)
    5. Capture evidence with red rectangles (using in-memory page images)
    6. Identify physical address
    7. Transmit jurisdiction information
    """

    # Pattern definitions
    NUMERIC_PATTERNS = [
        r'(\d{1,3})\s*(?:IN|"|″)\s*(?:WIDTH|WIDE|W)',
        r'WIDTH\s*[:=]\s*(\d{1,3})',
        r'DOOR\s*(?:WIDTH|WIDE)\s*[:=]\s*(\d{1,3})',
        r'(\d{1,3})\s*\"\s*X\s*(\d{1,3})\s*\"',
    ]

    KEYWORDS = [
        "FIRE EXIT", "EXIT", "EMERGENCY", "EMERGENCY EXIT",
        "DOOR", "DOORS", "WIDTH", "WIDE",
        "SAFETY", "SAFE", "OCCUPANCY", "CAPACITY",
        "BUILDING CODE", "ZONING", "PERMIT",
        "STAIR", "STAIRWAY", "STAIRCASE", "CORRIDOR", "HALLWAY",
        "EGRESS", "MEANS OF EGRESS", "EXIT ACCESS"
    ]

    SAFETY_TERMS = [
        "SAFETY", "OCCUPANCY", "CAPACITY", "FIRE", "FIRE SAFETY",
        "ALARM", "SPRINKLER", "FIRE EXTINGUISHER", "SMOKE DETECTOR",
        "EMERGENCY LIGHTING", "EXIT SIGN", "FIRE DOOR", "FIRE RATING"
    ]

    REGULATORY_TERMS = [
        "BUILDING CODE", "ZONING", "PERMIT", "INSPECTION",
        "OCCUPANCY PERMIT", "BUILDING PERMIT", "CODE COMPLIANCE",
        "REGULATORY", "APPROVAL", "CERTIFICATION"
    ]

    def __init__(self):
        super().__init__("PlanInspector", "visual_scanner")
        self.dpi = 200
        self.padding = 20
        self.supported_extensions = ['.pdf']
        self.evidence_dir = Path("/tmp/cais_evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def analyze(self, document: Document) -> Dict[str, Any]:
        """
        Main analysis method for PlanInspector (using a Document model instance).

        Args:
            document: Document object containing the PDF path

        Returns:
            dict: Analysis results with violations and evidence
        """
        logger.info(f"PlanInspector analyzing document: {document.id}")
        return self._perform_analysis(document.file_path, document_id=document.id)

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF directly from a file path.

        This method performs the same OCR and analysis pipeline as `analyze()`,
        but accepts a file path string instead of a Document object.

        Args:
            file_path: Path to the PDF file to analyze

        Returns:
            dict: Analysis results with violations and evidence
        """
        logger.info(f"PlanInspector analyzing file: {file_path}")
        return self._perform_analysis(file_path)

    def _perform_analysis(self, file_path: str, document_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Internal method that performs the actual analysis pipeline on a given PDF file.

        Args:
            file_path: Path to the PDF file
            document_id: Optional document ID (for logging and result metadata)

        Returns:
            dict: Analysis results with violations and evidence
        """
        # Step 1: Convert PDF pages to in-memory images at 200 DPI
        # (only for evidence capture, not for OCR)
        page_images = self._get_page_images(file_path)
        logger.info(f"Loaded {len(page_images)} pages as images for evidence")

        # Step 2: Run OCR directly on PDF (using pdf2image internally, but no saved files)
        ocr_results = self._run_ocr_on_pdf(file_path)

        # Step 3: Extract text and page-level data from OCR results
        full_text = "\n".join([r['text'] for r in ocr_results])
        page_texts = [r['text'] for r in ocr_results]

        # Step 4: Analyze text for violations
        violations = self._analyze_text(full_text, page_texts, ocr_results)

        # Step 5: Extract address and jurisdiction from text
        address = self._extract_address_from_text(full_text)
        jurisdiction = self._extract_jurisdiction_from_text(full_text)

        # Step 6: Capture evidence for each violation (using page images)
        for violation in violations:
            page_num = violation.get('page_num', 0)
            if page_num < len(page_images) and violation.get('coordinates'):
                evidence = self._capture_evidence(
                    page_images[page_num],
                    violation['coordinates'],
                    self.padding
                )
                violation['evidence_path'] = evidence

        return {
            'document_id': str(document_id) if document_id else None,
            'pages': len(page_images),
            'address': address,
            'jurisdiction': jurisdiction,
            'violations': violations,
            'text_length': len(full_text),
            'status': 'completed'
        }

    def _get_page_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Get page images for evidence capture (in-memory, no files saved).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of PIL Images
        """
        try:
            images = pdf2image.convert_from_path(pdf_path, dpi=self.dpi)
            logger.info(f"Loaded {len(images)} page images for evidence")
            return images
        except Exception as e:
            logger.error(f"Error loading PDF pages: {e}")
            return []

    def _run_ocr_on_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Run OCR directly on PDF at 200 DPI.

        Uses pdf2image internally to render pages in memory,
        but does NOT save any image files.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of dicts with page_num, text, and confidence
        """
        results = []
        try:
            # Convert to images in memory (no files)
            images = pdf2image.convert_from_path(pdf_path, dpi=self.dpi)

            for page_num, image in enumerate(images):
                # Run OCR on the in-memory image
                page_text = pytesseract.image_to_string(image, lang='eng')
                results.append({
                    'page_num': page_num,
                    'text': page_text,
                    'confidence': 1.0  # Placeholder for confidence
                })
                logger.info(f"  Page {page_num + 1}: {len(page_text)} chars via OCR")

            logger.info(f"OCR completed on {len(images)} pages at {self.dpi} DPI")
            return results

        except Exception as e:
            logger.error(f"Error running OCR on PDF: {e}")
            return []

    def _analyze_text(self, full_text: str, page_texts: List[str], ocr_results: List[Dict]) -> List[Dict[str, Any]]:
        """
        Analyze OCR text for violations.

        Args:
            full_text: Full text content
            page_texts: List of text per page
            ocr_results: Full OCR results with position data

        Returns:
            List of violations
        """
        violations = []

        if not full_text or len(full_text.strip()) < 10:
            return violations

        for page_num, page_text in enumerate(page_texts):
            # Detect numeric patterns (door widths)
            for pattern in self.NUMERIC_PATTERNS:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    width = int(match.group(1))
                    if width < 32:
                        # Approximate coordinates from text position
                        coords = self._get_text_location_from_text(page_text, match.group(0))
                        violations.append({
                            'type': 'door_width',
                            'severity': 'critical' if width < 30 else 'warning',
                            'description': f'Door width {width}" (below standard 32" minimum)',
                            'page_num': page_num,
                            'coordinates': coords,
                            'code_reference': 'IBC 1005.3.1 - Means of Egress Door Width',
                            'evidence': None
                        })

            # Detect keywords
            for keyword in self.KEYWORDS:
                if keyword.lower() in page_text.lower():
                    coords = self._get_text_location_from_text(page_text, keyword)
                    violations.append({
                        'type': 'keyword',
                        'severity': 'warning',
                        'description': f'Keyword found: {keyword}',
                        'page_num': page_num,
                        'coordinates': coords,
                        'code_reference': self._get_code_reference(keyword),
                        'evidence': None
                    })

        return violations

    def _get_text_location_from_text(self, page_text: str, search_text: str) -> Dict[str, int]:
        """
        Approximate coordinates of text on the page from text position.

        Args:
            page_text: The text content of the page
            search_text: The text to locate

        Returns:
            dict: Approximate coordinates
        """
        lines = page_text.split('\n')
        for i, line in enumerate(lines):
            if search_text.lower() in line.lower():
                # Estimate position based on line index and text length
                y = 50 + (i * 20)
                x = 50 + (len(line[:line.lower().find(search_text.lower())]) * 5)
                return {
                    'x': max(0, x),
                    'y': max(0, y),
                    'width': max(50, len(search_text) * 8),
                    'height': 25
                }
        return {'x': 100, 'y': 100, 'width': 200, 'height': 40}

    def _capture_evidence(self, image: Image.Image, coordinates: Dict, padding: int) -> str:
        """
        Capture evidence with red rectangle and padding.

        Args:
            image: PIL Image
            coordinates: Dict with x, y, width, height
            padding: Padding around the violation

        Returns:
            str: Path to saved evidence image
        """
        evidence = image.copy()
        draw = ImageDraw.Draw(evidence)

        x = coordinates.get('x', 100) - padding
        y = coordinates.get('y', 100) - padding
        width = coordinates.get('width', 200) + padding * 2
        height = coordinates.get('height', 40) + padding * 2

        x = max(0, x)
        y = max(0, y)
        width = min(width, evidence.width - x)
        height = min(height, evidence.height - y)

        draw.rectangle(
            [(x, y), (x + width, y + height)],
            outline='red',
            width=3
        )

        evidence_path = self.evidence_dir / f"evidence_{uuid.uuid4().hex[:8]}.png"
        evidence.save(evidence_path)

        logger.info(f"Evidence captured: {evidence_path}")
        return str(evidence_path)

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract physical address from text."""
        if not text:
            return None

        patterns = [
            r'(?:address|location|site|project)\s*:?\s*([^\n]{5,100})',
            r'(\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln|court|ct|way|circle|cir|place|pl|terrace|ter)\.?\s*[A-Z]{2}\s*\d{5})',
            r'(\d{1,5}\s+[A-Za-z]+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s*,\s*[A-Z]{2}\s*\d{5})',
            r'(?:at|located at|from)\s+([^\n]{10,100})',
            r'(\d{1,5}\s+[A-Za-z]+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+[A-Z]{2}\s*\d{5})',
        ]

        for line in text.split('\n'):
            line = line.strip()
            if len(line) < 10:
                continue
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    address = match.group(1).strip()
                    address = re.sub(r'\s+', ' ', address)
                    if len(address) > 5 and any(char.isdigit() for char in address):
                        return address
        return None

    def _extract_jurisdiction_from_text(self, text: str) -> Optional[str]:
        """Extract jurisdiction from text."""
        if not text:
            return None
        text_upper = text.upper()
        if 'MIAMI' in text_upper or 'FLORIDA' in text_upper:
            return 'Miami-Dade County, Florida'
        elif 'NEW YORK' in text_upper or 'NYC' in text_upper:
            return 'New York City, New York'
        elif 'LOS ANGELES' in text_upper or 'LA' in text_upper:
            return 'Los Angeles, California'
        elif 'CHICAGO' in text_upper:
            return 'Chicago, Illinois'
        elif 'HOUSTON' in text_upper:
            return 'Houston, Texas'
        elif 'SAN FRANCISCO' in text_upper:
            return 'San Francisco, California'
        elif 'SEATTLE' in text_upper:
            return 'Seattle, Washington'
        elif 'DENVER' in text_upper:
            return 'Denver, Colorado'
        elif 'BOSTON' in text_upper:
            return 'Boston, Massachusetts'
        elif 'WASHINGTON' in text_upper or 'DC' in text_upper:
            return 'Washington, D.C.'
        elif 'PHILADELPHIA' in text_upper:
            return 'Philadelphia, Pennsylvania'
        elif 'DALLAS' in text_upper:
            return 'Dallas, Texas'
        elif 'SAN DIEGO' in text_upper:
            return 'San Diego, California'
        elif 'AUSTIN' in text_upper:
            return 'Austin, Texas'
        elif 'JACKSONVILLE' in text_upper:
            return 'Jacksonville, Florida'
        # Fallback: check for any US state abbreviation
        state_match = re.search(r'\b([A-Z]{2})\b', text)
        if state_match:
            return f'US-{state_match.group(1)}'
        return None

    def _get_code_reference(self, keyword: str) -> str:
        """Get code reference for a keyword."""
        code_references = {
            'FIRE EXIT': 'IBC 1007 - Means of Egress for Fire Safety',
            'EMERGENCY': 'IBC 1008 - Emergency Egress',
            'DOOR': 'IBC 1005.3.1 - Door Width Requirements',
            'WIDTH': 'IBC 1005.3.1 - Minimum Door Width',
            'SAFETY': 'OSHA 1926 - Safety Standards',
            'OCCUPANCY': 'IBC 1004 - Occupant Load',
            'CAPACITY': 'IBC 1004 - Occupant Capacity',
        }
        return code_references.get(keyword.upper(), 'IBC General Requirements')
