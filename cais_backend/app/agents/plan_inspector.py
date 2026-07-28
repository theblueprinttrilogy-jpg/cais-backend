#!/usr/bin/env python3
"""
PlanInspector - OCR-based detection for scanned construction plans.
Detects door width, railing height, and riser height violations.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter
import fitz
import pdf2image
import pytesseract

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@dataclass
class Violation:
    type: str
    page_number: int
    detected_value: float
    required_value: float
    unit: str
    code_reference: str
    code_description: str
    context_text: str
    coordinates: Tuple[int, int, int, int]
    screenshot_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "type": self.type,
            "page_number": self.page_number,
            "detected_value": self.detected_value,
            "required_value": self.required_value,
            "unit": self.unit,
            "code_reference": self.code_reference,
            "code_description": self.code_description,
            "context_text": self.context_text,
            "coordinates": {
                "x": self.coordinates[0],
                "y": self.coordinates[1],
                "width": self.coordinates[2],
                "height": self.coordinates[3]
            },
            "screenshot_path": self.screenshot_path,
            "timestamp": self.timestamp
        }

class PlanInspector:
    CODE_REFERENCE_DOOR = "IBC 1006.2.1"
    CODE_DESCRIPTION_DOOR = "Exit access door opening width must be at least 32 inches (813 mm)."
    CODE_REFERENCE_RAILING = "IBC 1015.2"
    CODE_DESCRIPTION_RAILING = "Guardrail height must be at least 42 inches (1067 mm)."
    CODE_REFERENCE_RISER = "IBC 1011.5.2"
    CODE_DESCRIPTION_RISER = "Stair riser height must not exceed 7 inches (178 mm)."

    PATTERNS = {
        'door_width': [
            re.compile(r'(?:door|puerta|egress|salida|exit|clear opening).*?(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg|mm)', re.IGNORECASE),
            re.compile(r'(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg)\s*(?:door|puerta|egress|salida)', re.IGNORECASE),
            re.compile(r'(\d{1,3}(?:\.\d+)?)\s*"', re.IGNORECASE),
        ],
        'railing_height': [
            re.compile(r'(?:railing|guardrail|baranda).*?(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg|cm)', re.IGNORECASE),
            re.compile(r'(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg)\s*(?:railing|guardrail|baranda)', re.IGNORECASE),
        ],
        'riser_height': [
            re.compile(r'(?:riser|contrahuella).*?(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg|cm)', re.IGNORECASE),
            re.compile(r'(\d{1,3}(?:\.\d+)?)\s*(?:in|"|inch|pulg)\s*(?:riser|contrahuella)', re.IGNORECASE),
        ]
    }
    CONTEXT_KEYWORDS = {
        'door_width': ['door', 'puerta', 'egress', 'salida', 'exit', 'clear', 'opening', 'ancho', 'width'],
        'railing_height': ['railing', 'guardrail', 'baranda', 'altura', 'height'],
        'riser_height': ['riser', 'contrahuella', 'altura', 'height', 'max', 'maximo'],
    }

    def __init__(self, dpi=250, min_door=32.0, min_railing=42.0, max_riser=7.0, output_dir=None):
        self.dpi = dpi
        self.min_door = min_door
        self.min_railing = min_railing
        self.max_riser = max_riser
        self.output_dir = output_dir
        self.violations = []

    def inspect(self, pdf_path: str, session_id: str = "default") -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        self.violations = []
        output_root = self._get_output_dir(session_id)
        screenshots_dir = output_root / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Processing {pdf_path.name} with OCR...")

        # Try fitz for text-based PDFs
        text_pages = self._extract_text_with_fitz(pdf_path)
        if text_pages:
            logger.info("Text-based PDF detected")
            for page_num, page_text in text_pages.items():
                self._inspect_text_page(page_text, page_num, pdf_path, screenshots_dir)
        else:
            # Fallback to OCR for scanned PDFs
            logger.info("Scanned PDF detected, using OCR")
            images = pdf2image.convert_from_path(pdf_path, dpi=self.dpi)
            for page_num, img in enumerate(images, start=1):
                self._inspect_ocr_page(img, page_num, screenshots_dir)

        return {
            "success": True,
            "session_id": session_id,
            "total_violations": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "screenshots_dir": str(screenshots_dir),
            "timestamp": datetime.now().isoformat()
        }

    def _extract_text_with_fitz(self, pdf_path: Path) -> Dict[int, str]:
        text_pages = {}
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            if text.strip():
                text_pages[page_num + 1] = text
        doc.close()
        return text_pages

    def _inspect_text_page(self, page_text: str, page_num: int, pdf_path: Path, screenshots_dir: Path):
        for vtype, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(page_text):
                    try:
                        value = float(match.group(1))
                    except (ValueError, IndexError):
                        continue
                    if not self._is_violation(vtype, value):
                        continue
                    context = page_text[max(0, match.start()-200):min(len(page_text), match.end()+200)]
                    if not self._has_context(context, vtype):
                        continue
                    screenshot_path = self._capture_region_from_page(pdf_path, page_num, match.start(), match.end(), page_text, screenshots_dir)
                    violation = Violation(
                        type=vtype,
                        page_number=page_num,
                        detected_value=value,
                        required_value=self._get_required(vtype),
                        unit="inches",
                        code_reference=self._get_code(vtype),
                        code_description=self._get_description(vtype),
                        context_text=context.strip(),
                        coordinates=(0,0,0,0),
                        screenshot_path=screenshot_path
                    )
                    self.violations.append(violation)
                    logger.info(f"Violation on page {page_num}: {vtype} = {value}\"")

    def _inspect_ocr_page(self, img: Image.Image, page_num: int, screenshots_dir: Path):
        img_gray = img.convert('L')
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(1.5)
        img_enhanced = img_enhanced.filter(ImageFilter.SHARPEN)
        img_bin = img_enhanced.point(lambda p: 255 if p > 180 else 0)
        ocr_data = pytesseract.image_to_data(img_bin, output_type=pytesseract.Output.DICT, config='--psm 6')
        for i, word in enumerate(ocr_data['text']):
            if not word or not word.strip():
                continue
            for vtype, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    match = pattern.search(word)
                    if not match:
                        continue
                    try:
                        value = float(match.group(1))
                    except (ValueError, IndexError):
                        continue
                    if not self._is_violation(vtype, value):
                        continue
                    context = self._get_context(ocr_data, i)
                    if not self._has_context(context, vtype):
                        continue
                    coords = self._get_bbox(ocr_data, i)
                    if not coords:
                        continue
                    crop = self._crop_and_annotate(img, coords, vtype)
                    screenshot_path = self._save_crop(crop, page_num, len(self.violations)+1, screenshots_dir)
                    violation = Violation(
                        type=vtype,
                        page_number=page_num,
                        detected_value=value,
                        required_value=self._get_required(vtype),
                        unit="inches",
                        code_reference=self._get_code(vtype),
                        code_description=self._get_description(vtype),
                        context_text=context.strip(),
                        coordinates=coords,
                        screenshot_path=screenshot_path
                    )
                    self.violations.append(violation)
                    logger.info(f"Violation on page {page_num}: {vtype} = {value}\"")

    # Helper methods
    def _is_violation(self, vtype, value):
        if vtype == 'door_width': return value < self.min_door
        if vtype == 'railing_height': return value < self.min_railing
        if vtype == 'riser_height': return value > self.max_riser
        return False
    def _get_required(self, vtype):
        return self.min_door if vtype == 'door_width' else self.min_railing if vtype == 'railing_height' else self.max_riser
    def _get_code(self, vtype):
        return self.CODE_REFERENCE_DOOR if vtype == 'door_width' else self.CODE_REFERENCE_RAILING if vtype == 'railing_height' else self.CODE_REFERENCE_RISER
    def _get_description(self, vtype):
        return self.CODE_DESCRIPTION_DOOR if vtype == 'door_width' else self.CODE_DESCRIPTION_RAILING if vtype == 'railing_height' else self.CODE_DESCRIPTION_RISER
    def _has_context(self, text, vtype):
        return any(k in text.lower() for k in self.CONTEXT_KEYWORDS.get(vtype, []))
    def _get_context(self, ocr_data, idx, window=5):
        start = max(0, idx - window)
        end = min(len(ocr_data['text']), idx + window + 1)
        return " ".join(w for w in ocr_data['text'][start:end] if w and w.strip())
    def _get_bbox(self, ocr_data, idx):
        try:
            return (ocr_data['left'][idx], ocr_data['top'][idx],
                    ocr_data['width'][idx], ocr_data['height'][idx])
        except:
            return None
    def _crop_and_annotate(self, img, coords, vtype):
        x, y, w, h = coords
        padding = 50
        x = max(0, x - padding); y = max(0, y - padding)
        w = min(img.width - x, w + 2*padding)
        h = min(img.height - y, h + 2*padding)
        crop = img.crop((x, y, x + w, y + h))
        draw = ImageDraw.Draw(crop)
        draw.rectangle([(0,0), (crop.width-1, crop.height-1)], outline="red", width=3)
        draw.text((10,10), vtype.replace('_',' ').upper(), fill="red")
        return crop
    def _save_crop(self, crop, page_num, idx, screenshots_dir):
        filename = f"violation_p{page_num}_{idx}.png"
        path = screenshots_dir / filename
        crop.save(path)
        return str(path)
    def _capture_region_from_page(self, pdf_path, page_num, start, end, text, screenshots_dir):
        # Simplified: capture full page with red border
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(10,10), (img.width-10, img.height-10)], outline="red", width=5)
            filename = f"violation_page{page_num}_{len(self.violations)+1}.png"
            path = screenshots_dir / filename
            img.save(path)
            doc.close()
            return str(path)
        except:
            return None
    def _get_output_dir(self, session_id):
        base = self.output_dir or Path(f"/tmp/cais_uploads/{session_id}")
        base.mkdir(parents=True, exist_ok=True)
        return base
