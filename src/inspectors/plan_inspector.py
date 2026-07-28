#!/usr/bin/env python3
"""
TASK 23: PlanInspector - Visual Violation Detection
Detects visual violations in construction plans using computer vision.
Extracts text, detects patterns, and captures evidence with RED boxes.
"""

import os
import sys
import json
import re
import hashlib
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import shutil

# PDF Processing - Using pdf2image directly
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import io

# OCR
import pytesseract


@dataclass
class ViolationEvidence:
    """Evidence of a violation found in a document."""
    violation_id: str
    document_name: str
    page_number: int
    coordinates: Dict[str, int]
    screenshot_path: str
    evidence_text: str
    detected_pattern: str
    severity: str
    code_id: Optional[str] = None
    jurisdiction: str = 'Unknown'
    hash: str = ''


class PlanInspector:
    """
    TASK 23: PlanInspector - Visual Violation Detection
    
    Scans construction plans and detects visual violations.
    Captures evidence with RED boxes for forensic documentation.
    """
    
    # Known violation patterns
    VIOLATION_PATTERNS = {
        'door_width': {
            'pattern': r'(?:door|exit|egress).*?(?:width|size|opening).*?(\d{1,3}(?:\.\d)?)\s*(?:in|"|inch)',
            'threshold': 32,
            'severity': 'critical',
            'code': 'IBC 1006.2.1',
            'description': 'Exit access door opening width less than 32 inches'
        },
        'guard_height': {
            'pattern': r'guard(?:rail)?\s*(?:height|top).*?(\d{1,3}(?:\.\d)?)\s*(?:in|"|inch)',
            'threshold': 42,
            'severity': 'high',
            'code': 'IBC 1015.2',
            'description': 'Guard height less than 42 inches'
        },
        'stair_tread': {
            'pattern': r'tread\s*(?:width|depth).*?(\d{1,3}(?:\.\d)?)\s*(?:in|"|inch)',
            'threshold': 11,
            'severity': 'high',
            'code': 'IBC 1011.5.2',
            'description': 'Stair tread depth less than 11 inches'
        },
        'stair_riser': {
            'pattern': r'riser\s*(?:height).*?(\d{1,3}(?:\.\d)?)\s*(?:in|"|inch)',
            'threshold': 7,
            'severity': 'high',
            'code': 'IBC 1011.5.2',
            'description': 'Stair riser height greater than 7 inches'
        },
        'handrail_height': {
            'pattern': r'handrail\s*(?:height).*?(\d{1,3}(?:\.\d)?)\s*(?:in|"|inch)',
            'threshold': 34,
            'severity': 'medium',
            'code': 'IBC 1014.3',
            'description': 'Handrail height less than 34 inches'
        },
        'ceiling_height': {
            'pattern': r'ceiling\s*(?:height).*?(\d{1,3}(?:\.\d)?)\s*(?:ft|feet|\')',
            'threshold': 7,
            'severity': 'medium',
            'code': 'IBC 1208.2',
            'description': 'Ceiling height less than 7 feet'
        }
    }
    
    def __init__(self, output_dir: str = "./evidence", dpi: int = 200):
        """
        Initialize the Plan Inspector.
        
        Args:
            output_dir: Directory to store evidence images
            dpi: Resolution for PDF conversion
        """
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi
        self.evidence: List[ViolationEvidence] = []
        
        # Database config
        self.db_host = '127.0.0.1'
        self.db_port = 5433
        self.db_name = 'cais_db'
        self.db_user = 'cais_user'
        self.db_password = 'cais_secure_password_2026'
        
        print("\n" + "="*70)
        print(" TASK 23: PLANINSPECTOR")
        print(" Visual Violation Detection")
        print("="*70)
        print(f" Output directory: {self.output_dir}")
        print(f" OCR DPI: {self.dpi}")
    
    async def inspect_pdf(self, pdf_path: str) -> List[ViolationEvidence]:
        """
        Inspect a PDF file for visual violations.
        
        Args:
            pdf_path: Path to the PDF document
            
        Returns:
            List of ViolationEvidence objects
        """
        pdf_path = Path(pdf_path).expanduser()
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        print(f"\n📄 Inspecting: {pdf_path.name}")
        print("-" * 50)
        
        # Create inspection directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        inspection_dir = self.output_dir / f"{pdf_path.stem}_{timestamp}"
        inspection_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Convert PDF to images
        print("   [1/4] Converting PDF to images...")
        images = self._pdf_to_images(pdf_path, inspection_dir)
        print(f"   ✅ {len(images)} pages converted")
        
        # Step 2: Extract text from each page
        print("\n   [2/4] Extracting text and detecting violations...")
        all_text = ""
        
        for page_num, image_path in enumerate(images, 1):
            text = self._extract_text_from_image(image_path)
            all_text += f"\n--- PAGE {page_num} ---\n{text}"
            
            # Detect violations on this page
            violations = self._detect_violations(text, image_path, page_num, inspection_dir)
            
            for violation in violations:
                evidence = ViolationEvidence(
                    violation_id=f"VIO-{timestamp}-{page_num:03d}-{len(self.evidence)+1:03d}",
                    document_name=pdf_path.name,
                    page_number=page_num,
                    coordinates=violation['coordinates'],
                    screenshot_path=violation['screenshot_path'],
                    evidence_text=violation['text'],
                    detected_pattern=violation['pattern'],
                    severity=violation['severity'],
                    code_id=violation.get('code_id'),
                    jurisdiction=violation.get('jurisdiction', 'Unknown')
                )
                self.evidence.append(evidence)
                print(f"   ⚠️ {evidence.severity.upper()}: {evidence.detected_pattern}")
        
        # Step 3: Save evidence to database
        print("\n   [3/4] Saving evidence to database...")
        await self._save_evidence_to_db()
        
        # Step 4: Generate report
        print("\n   [4/4] Generating inspection report...")
        report = self._generate_report(pdf_path, inspection_dir)
        
        print(f"\n✅ Inspection complete!")
        print(f"   Violations found: {len(self.evidence)}")
        print(f"   Evidence saved: {inspection_dir}")
        
        return self.evidence
    
    def _pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """
        Convert PDF pages to images using pdf2image.
        
        Returns:
            List of image file paths
        """
        images = []
        
        try:
            print(f"   Converting PDF to images using pdf2image...")
            pil_images = convert_from_path(str(pdf_path), dpi=self.dpi)
            
            for page_num, img in enumerate(pil_images, 1):
                image_path = output_dir / f"page_{page_num:03d}.png"
                img.save(image_path, 'PNG')
                images.append(image_path)
            
        except Exception as e:
            print(f"   ❌ pdf2image failed: {e}")
            print("   Please install poppler-utils:")
            print("   sudo apt install poppler-utils")
            raise
        
        return images
    
    def _extract_text_from_image(self, image_path: Path) -> str:
        """
        Extract text from an image using OCR.
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"   ⚠️ OCR failed: {e}")
            return ""
    
    def _detect_violations(self, text: str, image_path: Path, page_num: int, output_dir: Path) -> List[Dict]:
        """
        Detect violations in the extracted text.
        
        Returns:
            List of violation dictionaries
        """
        violations = []
        text_lower = text.lower()
        
        for pattern_name, pattern_config in self.VIOLATION_PATTERNS.items():
            matches = re.findall(pattern_config['pattern'], text_lower, re.IGNORECASE)
            
            for match in matches:
                try:
                    # Extract numeric value
                    if isinstance(match, tuple):
                        value = float(match[0])
                    else:
                        value = float(match)
                    
                    # Check against threshold
                    threshold = pattern_config['threshold']
                    
                    # Determine if violation
                    if 'maximum' in pattern_config.get('description', '').lower():
                        if value <= threshold:
                            continue
                    else:
                        if value >= threshold:
                            continue
                    
                    # Find the full text around the match
                    full_text = self._find_text_context(text, str(match), context_chars=200)
                    
                    # Create screenshot with RED box
                    screenshot_path = self._create_screenshot_with_red_box(
                        image_path, 
                        page_num,
                        match_text=str(match),
                        output_dir=output_dir,
                        pattern_name=pattern_name
                    )
                    
                    # Get coordinates
                    coords = self._find_coordinates(image_path, str(match))
                    
                    violations.append({
                        'pattern': pattern_name,
                        'severity': pattern_config['severity'],
                        'code_id': pattern_config.get('code'),
                        'threshold': threshold,
                        'value': value,
                        'text': full_text,
                        'coordinates': coords,
                        'screenshot_path': screenshot_path,
                        'jurisdiction': 'International'
                    })
                    
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️ Error parsing match: {e}")
                    continue
        
        return violations
    
    def _find_text_context(self, text: str, search_term: str, context_chars: int = 200) -> str:
        """Find text context around a search term."""
        index = text.lower().find(search_term.lower())
        
        if index == -1:
            return search_term
        
        start = max(0, index - context_chars // 2)
        end = min(len(text), index + len(search_term) + context_chars // 2)
        
        context = text[start:end]
        
        return context
    
    def _find_coordinates(self, image_path: Path, text: str) -> Dict[str, int]:
        """
        Find coordinates of text in the image.
        
        Returns:
            Dictionary with x, y, width, height
        """
        try:
            image = Image.open(image_path)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            for i, word in enumerate(data['text']):
                if text.lower() in word.lower():
                    return {
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    }
                    
        except Exception as e:
            print(f"   ⚠️ Could not find coordinates: {e}")
        
        # Default coordinates if not found
        return {'x': 100, 'y': 100, 'width': 200, 'height': 50}
    
    def _create_screenshot_with_red_box(
        self, 
        image_path: Path, 
        page_num: int,
        match_text: str,
        output_dir: Path,
        pattern_name: str
    ) -> str:
        """
        Create a screenshot with a RED box around the violation.
        
        Returns:
            Path to the screenshot file
        """
        try:
            # Load image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            # Find coordinates
            coords = self._find_coordinates(image_path, match_text)
            
            # Add padding
            padding = 30
            x = max(0, coords.get('x', 100) - padding)
            y = max(0, coords.get('y', 100) - padding)
            width = coords.get('width', 100) + padding * 2
            height = coords.get('height', 50) + padding * 2
            
            # Draw RED box
            box_color = (204, 0, 0)
            draw.rectangle(
                [(x, y), (x + width, y + height)],
                outline=box_color,
                width=4
            )
            
            # Add "VIOLATION" label
            label_x = x
            label_y = y - 25
            if label_y < 0:
                label_y = y + 10
            
            draw.rectangle(
                [(label_x, label_y), (label_x + 150, label_y + 25)],
                fill=(204, 0, 0, 200)
            )
            
            try:
                font = ImageFont.truetype("Arial", 14)
            except:
                font = ImageFont.load_default()
            
            draw.text(
                (label_x + 5, label_y + 3),
                "VIOLATION",
                fill=(255, 255, 255),
                font=font
            )
            
            # Add page number
            try:
                font_small = ImageFont.truetype("Arial", 10)
            except:
                font_small = ImageFont.load_default()
            
            draw.text(
                (10, image.height - 30),
                f"Page: {page_num} | Pattern: {pattern_name}",
                fill=(100, 100, 100, 150),
                font=font_small
            )
            
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            screenshot_path = output_dir / f"violation_page{page_num}_{timestamp}.png"
            image.save(screenshot_path, 'PNG')
            
            return str(screenshot_path)
            
        except Exception as e:
            print(f"   ⚠️ Error creating screenshot: {e}")
            return str(image_path)
    
    async def _save_evidence_to_db(self):
        """Save evidence to the database."""
        if not self.evidence:
            print("   No evidence to save")
            return
        
        try:
            conn = await asyncpg.connect(
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            
            for evidence in self.evidence:
                await conn.execute("""
                    INSERT INTO cais.violations 
                    (violation_id, audit_id, code_id, document_page, coordinates, screenshot_path, severity, fact_hash)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (violation_id) DO UPDATE SET
                        screenshot_path = EXCLUDED.screenshot_path,
                        updated_at = NOW()
                """,
                    evidence.violation_id,
                    'AUDIT-001',
                    evidence.code_id,
                    evidence.page_number,
                    json.dumps(evidence.coordinates),
                    evidence.screenshot_path,
                    evidence.severity,
                    evidence.hash
                )
            
            # Insert WORM entry
            await conn.execute("""
                INSERT INTO cais.worm_ledger 
                (sequence, event_type, payload, actor, previous_hash, node_id)
                SELECT 
                    COALESCE(MAX(sequence), -1) + 1,
                    'VIOLATIONS_DETECTED',
                    jsonb_build_object('total', $1, 'severity', 'mixed'),
                    'plan_inspector',
                    COALESCE(MAX(hash), '0' || REPEAT('0', 63)),
                    'local'
                FROM cais.worm_ledger
            """, len(self.evidence))
            
            await conn.close()
            print(f"   ✅ {len(self.evidence)} violations saved to database")
            
        except Exception as e:
            print(f"   ⚠️ Could not save to database: {e}")
    
    def _generate_report(self, pdf_path: Path, output_dir: Path) -> Dict:
        """Generate an inspection report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'document_name': pdf_path.name,
            'total_violations': len(self.evidence),
            'severity_breakdown': {
                'critical': sum(1 for e in self.evidence if e.severity == 'critical'),
                'high': sum(1 for e in self.evidence if e.severity == 'high'),
                'medium': sum(1 for e in self.evidence if e.severity == 'medium'),
                'low': sum(1 for e in self.evidence if e.severity == 'low')
            },
            'evidence': [
                {
                    'violation_id': e.violation_id,
                    'page': e.page_number,
                    'severity': e.severity,
                    'pattern': e.detected_pattern,
                    'screenshot': e.screenshot_path,
                    'code_id': e.code_id
                }
                for e in self.evidence
            ]
        }
        
        # Save report
        report_path = output_dir / 'inspection_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


async def main():
    """Test the PlanInspector."""
    import glob
    
    print("\n" + "="*70)
    print(" PLANINSPECTOR - TEST RUN")
    print("="*70)
    
    # Check if poppler is installed
    import subprocess
    try:
        subprocess.run(['pdftoppm', '-v'], capture_output=True, check=True)
    except:
        print("\n⚠️ poppler-utils not found. Installing...")
        subprocess.run(['sudo', 'apt', 'update'], check=False)
        subprocess.run(['sudo', 'apt', 'install', '-y', 'poppler-utils'], check=False)
    
    # Find PDFs to test
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    
    if not pdf_files:
        print("No PDFs found. Creating a test PDF...")
        
        # Try to use fitz for creating test PDF
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            
            test_text = """
            CONSTRUCTION PLANS - TEST DOCUMENT
            
            EXIT DOOR: 30 inches wide
            GUARDRAIL HEIGHT: 36 inches
            STAIR TREAD: 9 inches depth
            STAIR RISER: 8 inches height
            HANDRAIL HEIGHT: 32 inches
            CEILING HEIGHT: 6.5 feet
            
            All dimensions are in inches unless noted.
            """
            
            page.insert_text((50, 50), test_text, fontsize=12)
            test_pdf = "/home/maxlo/PROMETHEUS/test_plan.pdf"
            doc.save(test_pdf)
            doc.close()
            pdf_files = [test_pdf]
        except:
            print("❌ Could not create test PDF. Please provide a PDF file.")
            return
    
    # Inspect the first PDF
    inspector = PlanInspector(output_dir="./evidence")
    await inspector.inspect_pdf(pdf_files[0])
    
    print("\n" + "="*70)
    print(" PLANINSPECTOR COMPLETE")
    print("="*70)
    print(f" Evidence saved in: {inspector.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
