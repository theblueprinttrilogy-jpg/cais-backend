# agents/plan_inspector.py - Multilingual Plan Inspector for CAIS v2.0
# Production-ready visual forensic inspector for blueprint PDFs.
# Supports automatic language detection, multilingual OCR, and semantic violation detection
# across construction codes (IBC, CTE, NFPA, etc.).
# Detects door width violations (< 32 inches or equivalent local metrics),
# captures evidence regions with configurable padding, and returns structured violation objects.

import os
import re
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import json

# PDF and image processing
try:
    from pdf2image import convert_from_path
except ImportError:
    raise ImportError("pdf2image is required. Install with: pip install pdf2image")

# OCR
try:
    import pytesseract
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError("pytesseract and PIL are required. Install with: pip install pytesseract pillow")

# Language detection
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed(0)
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None

# Pydantic
from pydantic import BaseModel, Field, validator

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------
class Violation(BaseModel):
    """Represents a detected code violation."""
    code_identifier: str = Field(..., description="Code identifier (e.g., IBC 1006.2.1)")
    description: str = Field(..., description="Human-readable violation description")
    page_number: int = Field(..., description="1-indexed page number")
    bbox: Tuple[int, int, int, int] = Field(..., description="(x1, y1, x2, y2) absolute coordinates")
    evidence_path: Optional[str] = Field(None, description="Path to cropped evidence image")
    detected_language: str = Field(..., description="Language code of the page text")
    confidence: float = Field(0.5, description="Confidence score (0-1)")

    class Config:
        arbitrary_types_allowed = True

class PlanInspectorConfig(BaseModel):
    """Configuration for PlanInspector."""
    dpi: int = Field(200, description="DPI for PDF conversion")
    evidence_padding: int = Field(20, description="Pixels to add around evidence bounding box")
    output_dir: Optional[str] = Field(None, description="Directory for evidence images")
    ocr_timeout: int = Field(120, description="OCR timeout in seconds")
    languages: List[str] = Field(
        default=["eng", "spa", "fra", "deu", "ita", "por", "nld", "rus", "jpn", "kor", "chi_sim", "chi_tra"],
        description="Tesseract language packs to try based on detection"
    )
    min_door_width_inches: float = Field(32.0, description="Minimum door width in inches (IBC 1006.2.1)")
    # Metric equivalent for international codes (e.g., 81 cm ~ 31.89 inches)
    min_door_width_cm: float = Field(81.28, description="Minimum door width in cm")
    # Mapping from language to common local code references
    code_reference_mapping: Dict[str, str] = Field(
        default={
            "en": "IBC 1006.2.1",
            "es": "CTE DB-SI",
            "fr": "NFPA 101 (French)",
            "de": "MBO",
            "it": "DM 18/05/2018",
            "pt": "DL 123/2021",
        },
        description="Code references per language"
    )

# ------------------------------------------------------------------------------
# PlanInspector Class
# ------------------------------------------------------------------------------
class PlanInspector:
    """
    Multilingual visual forensic inspector for blueprint PDFs.
    Detects code violations (door width) using OCR and language-specific patterns.
    """

    def __init__(self, config: Optional[PlanInspectorConfig] = None):
        """
        Initialize the PlanInspector.

        Args:
            config: Optional configuration; otherwise uses defaults or environment.
        """
        if config is None:
            # Load from environment if needed
            config = PlanInspectorConfig()
        self.config = config
        self.output_dir = Path(config.output_dir) if config.output_dir else Path(tempfile.mkdtemp(prefix="plan_inspector_"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Regex patterns for width measurements (inches and cm)
        # Pattern for inches: "32 IN", "32\"", "32in", "32 inches", etc.
        self.inch_pattern = re.compile(
            r'(\d{1,3}(?:\.\d+)?)\s*(?:IN|"|inches|inch|in\b)',
            re.IGNORECASE
        )
        # Pattern for centimeters: "81 cm", "81cm", "81 centimetros", etc.
        self.cm_pattern = re.compile(
            r'(\d{1,3}(?:\.\d+)?)\s*(?:CM|cm|centimeters|centimetres|centímetros|centimetros)',
            re.IGNORECASE
        )

        # Language code mapping for Tesseract
        self.lang_map = {
            'en': 'eng',
            'es': 'spa',
            'fr': 'fra',
            'de': 'deu',
            'it': 'ita',
            'pt': 'por',
            'nl': 'nld',
            'ru': 'rus',
            'ja': 'jpn',
            'ko': 'kor',
            'zh-cn': 'chi_sim',
            'zh-tw': 'chi_tra',
        }
        # Fallback languages if detection fails
        self.default_lang = 'eng'

        logger.info(
            f"PlanInspector initialized: dpi={self.config.dpi}, padding={self.config.evidence_padding}, "
            f"output_dir={self.output_dir}, min_door_width_inches={self.config.min_door_width_inches}, "
            f"min_door_width_cm={self.config.min_door_width_cm}"
        )

    def _detect_language(self, text: str) -> str:
        """
        Detect the language of the provided text.

        Returns:
            ISO 639-1 language code (e.g., 'en', 'es'), falling back to 'en'.
        """
        if not text or len(text.strip()) < 10:
            return 'en'
        if LANGDETECT_AVAILABLE:
            try:
                lang = detect(text)
                if lang:
                    return lang
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")
        # Fallback heuristic: check for common words
        text_lower = text.lower()
        if re.search(r'\b(the|and|for|with|this|that|have)\b', text_lower):
            return 'en'
        if re.search(r'\b(el|la|los|las|un|una|y|que|en|por|para)\b', text_lower):
            return 'es'
        if re.search(r'\b(le|la|les|et|pour|avec|sur|par|dans)\b', text_lower):
            return 'fr'
        if re.search(r'\b(der|die|das|und|zu|mit|von|für)\b', text_lower):
            return 'de'
        if re.search(r'\b(il|lo|la|e|che|per|di|da|in|su)\b', text_lower):
            return 'it'
        if re.search(r'\b(o|a|os|as|um|uma|e|que|no|na|por|para)\b', text_lower):
            return 'pt'
        return 'en'

    def _get_tesseract_lang(self, lang_code: str) -> str:
        """Map ISO language code to Tesseract language pack string."""
        # Handle multi-language fallback: try the specific, then fallback to eng+spa etc.
        # For simplicity, we return the mapped pack or 'eng' if not found.
        return self.lang_map.get(lang_code, 'eng')

    def _convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert a PDF file to a list of PIL Images.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of PIL Images (one per page).
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Converting PDF to images: {pdf_path}")
        try:
            images = convert_from_path(pdf_path, dpi=self.config.dpi)
            logger.info(f"Converted {len(images)} pages.")
            return images
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise

    def _ocr_page(self, image: Image.Image, lang: str) -> Tuple[str, Dict]:
        """
        Perform OCR on a single page image with specified language.

        Returns:
            Tuple of (full_text, ocr_data_dict) where ocr_data contains word-level bboxes.
        """
        # Tesseract language string: e.g., 'eng+spa' for multiple languages
        tesseract_lang = self._get_tesseract_lang(lang)
        # Optionally add fallback languages? We'll just use the primary.
        try:
            # Get full text
            text = pytesseract.image_to_string(image, lang=tesseract_lang)
            # Get detailed data for bounding boxes
            ocr_data = pytesseract.image_to_data(
                image,
                lang=tesseract_lang,
                output_type=pytesseract.Output.DICT
            )
            return text, ocr_data
        except Exception as e:
            logger.error(f"OCR failed for language {lang}: {e}")
            # Try with English as fallback
            try:
                text = pytesseract.image_to_string(image, lang='eng')
                ocr_data = pytesseract.image_to_data(image, lang='eng', output_type=pytesseract.Output.DICT)
                logger.warning("OCR fallback to English succeeded.")
                return text, ocr_data
            except Exception as e2:
                logger.error(f"OCR fallback failed: {e2}")
                return "", {}

    def _detect_violations(
        self,
        text: str,
        ocr_data: Dict,
        page_num: int,
        language: str
    ) -> List[Violation]:
        """
        Detect door width violations from OCR text and data.

        Returns:
            List of Violation objects.
        """
        violations = []
        # Determine which code reference to use
        code_ref = self.config.code_reference_mapping.get(language, "IBC 1006.2.1")

        # Find all width measurements in inches
        for match in self.inch_pattern.finditer(text):
            try:
                width_value = float(match.group(1))
                if width_value < self.config.min_door_width_inches:
                    bbox = self._get_bbox_for_match(match, ocr_data, text)
                    if bbox:
                        violation = Violation(
                            code_identifier=code_ref,
                            description=f"Door width {width_value}\" less than required {self.config.min_door_width_inches}\" (local code {code_ref})",
                            page_number=page_num,
                            bbox=bbox,
                            evidence_path=None,
                            detected_language=language,
                            confidence=0.7
                        )
                        violations.append(violation)
            except ValueError:
                continue

        # Find all width measurements in centimeters
        for match in self.cm_pattern.finditer(text):
            try:
                width_value = float(match.group(1))
                if width_value < self.config.min_door_width_cm:
                    # Optionally convert to inches for consistency? We'll keep cm.
                    bbox = self._get_bbox_for_match(match, ocr_data, text)
                    if bbox:
                        violation = Violation(
                            code_identifier=code_ref,
                            description=f"Door width {width_value}cm less than required {self.config.min_door_width_cm}cm (local code {code_ref})",
                            page_number=page_num,
                            bbox=bbox,
                            evidence_path=None,
                            detected_language=language,
                            confidence=0.7
                        )
                        violations.append(violation)
            except ValueError:
                continue

        return violations

    def _get_bbox_for_match(
        self,
        match: re.Match,
        ocr_data: Dict,
        full_text: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Given a regex match object, find the corresponding bounding box in OCR data.
        Returns (x1, y1, x2, y2) or None if not found.
        """
        start_pos = match.start()
        # We need to locate the word containing this position in the OCR data.
        # OCR data has a list of 'text' entries with corresponding positions.
        # We'll accumulate character positions.
        char_pos = 0
        for i, word in enumerate(ocr_data.get("text", [])):
            if not word or word.strip() == "":
                continue
            word_len = len(word)
            # Check if this word contains the match start position
            if char_pos <= start_pos < char_pos + word_len:
                # Found the word; get its bbox
                if (i < len(ocr_data.get("left", [])) and
                    i < len(ocr_data.get("top", [])) and
                    i < len(ocr_data.get("width", [])) and
                    i < len(ocr_data.get("height", []))):
                    x = ocr_data["left"][i]
                    y = ocr_data["top"][i]
                    w = ocr_data["width"][i]
                    h = ocr_data["height"][i]
                    return (x, y, x + w, y + h)
                else:
                    break
            char_pos += word_len + 1  # +1 for space (approximate)
        return None

    def _capture_evidence(
        self,
        image: Image.Image,
        bbox: Tuple[int, int, int, int],
        page_num: int,
        violation_idx: int,
        language: str
    ) -> str:
        """
        Crop a region from the page image with padding and save as evidence.

        Returns:
            File path to the saved evidence image.
        """
        x1, y1, x2, y2 = bbox
        pad = self.config.evidence_padding
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(image.width, x2 + pad)
        y2 = min(image.height, y2 + pad)

        crop = image.crop((x1, y1, x2, y2))
        evidence_filename = f"evidence_page{page_num}_{violation_idx}_{language}.png"
        evidence_path = self.output_dir / evidence_filename
        crop.save(evidence_path, "PNG")
        logger.debug(f"Evidence saved: {evidence_path}")
        return str(evidence_path)

    def inspect_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Main entry point: inspect a PDF for violations.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of violation dictionaries (including evidence paths).
        """
        logger.info(f"Inspecting PDF: {pdf_path}")

        # Convert PDF to images
        images = self._convert_pdf_to_images(pdf_path)

        all_violations = []
        evidence_counter = 0

        for page_num, img in enumerate(images, start=1):
            logger.info(f"Processing page {page_num}/{len(images)}")

            # First, detect language using a quick OCR or page text
            # We'll do a quick OCR with English first to get text for language detection
            # This is a performance trade-off; we could use the main OCR later.
            try:
                preview_text = pytesseract.image_to_string(img, lang='eng')
            except Exception:
                preview_text = ""
            lang = self._detect_language(preview_text)
            logger.debug(f"Page {page_num} detected language: {lang}")

            # Perform full OCR with appropriate language
            text, ocr_data = self._ocr_page(img, lang)
            if not text:
                logger.warning(f"No text extracted from page {page_num}")
                continue

            # Detect violations
            page_violations = self._detect_violations(text, ocr_data, page_num, lang)
            if not page_violations:
                logger.debug(f"No violations found on page {page_num}")
                continue

            # Capture evidence for each violation
            for v in page_violations:
                try:
                    evidence_path = self._capture_evidence(
                        img,
                        v.bbox,
                        page_num,
                        evidence_counter,
                        lang
                    )
                    v.evidence_path = evidence_path
                    evidence_counter += 1
                except Exception as e:
                    logger.error(f"Failed to capture evidence for violation on page {page_num}: {e}")

            all_violations.extend(page_violations)

        # Convert to list of dicts
        result = [v.dict() for v in all_violations]
        logger.info(f"Inspection complete. Found {len(result)} violations.")
        return result

    def close(self) -> None:
        """Clean up temporary resources."""
        # If output_dir was temporary, we could delete it; but we might keep evidence.
        # We'll just log.
        logger.info("PlanInspector closed.")

# ------------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python plan_inspector.py <path_to_pdf>")
        sys.exit(1)

    pdf_file = sys.argv[1]
    inspector = PlanInspector()
    violations = inspector.inspect_pdf(pdf_file)
    print(f"Found {len(violations)} violations:")
    for v in violations:
        print(f"  Page {v['page_number']}: {v['description']} (language: {v['detected_language']})")
        if v['evidence_path']:
            print(f"    Evidence: {v['evidence_path']}")
    inspector.close()
