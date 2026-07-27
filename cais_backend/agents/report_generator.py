# agents/report_generator.py - Report Generator for CAIS v2.0
# Production-ready agent that compiles forensic visual evidence (cropped images of violations)
# and matching building code legal references into a professional, multi-column PDF report
# using ReportLab. Ensures strict adherence to forensic auditing standards:
# every violation is visually documented, contextualized with statutory law,
# and formatted to be legally defensible for inspectors and attorneys.

import os
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator
from PIL import Image

# ReportLab imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Pydantic Models for Input Data and Configuration
# ------------------------------------------------------------------------------
class ViolationEvidence(BaseModel):
    """A single violation with its evidence and legal context."""
    page_number: int = Field(..., description="Page number in the original document")
    evidence_image_path: str = Field(..., description="Path to the cropped evidence PNG")
    code_identifier: str = Field(..., description="Code section (e.g., IBC 1006.2.1)")
    description: str = Field(..., description="Human-readable violation description")
    legal_reference: Optional[str] = Field(None, description="Full legal text or reference")
    confidence: float = Field(0.0, description="Confidence score (0-1)")
    coordinates: Tuple[int, int, int, int] = Field(..., description="Bounding box (x1,y1,x2,y2)")

    @validator('evidence_image_path')
    def validate_image_path(cls, v):
        if not os.path.isfile(v):
            raise ValueError(f"Evidence image not found: {v}")
        return v

class ReportConfig(BaseModel):
    """Configuration for the report generation."""
    title: str = Field("CAIS Forensic Inspection Report", description="Report title")
    author: str = Field("CAIS v2.0", description="Author name")
    output_dir: str = Field("./reports", description="Directory to save the PDF report")
    page_size: str = Field("letter", description="Page size: 'letter' or 'A4'")
    logo_path: Optional[str] = Field(None, description="Path to a logo image for the cover")
    max_evidence_width_inches: float = Field(3.5, description="Max width of evidence image in inches")
    max_evidence_height_inches: float = Field(4.0, description="Max height of evidence image in inches")
    include_summary_table: bool = Field(True, description="Include a summary table of all violations")

    @validator('output_dir')
    def create_output_dir(cls, v):
        os.makedirs(v, exist_ok=True)
        return v

    @validator('page_size')
    def validate_page_size(cls, v):
        if v.lower() not in ('letter', 'a4'):
            raise ValueError("page_size must be 'letter' or 'A4'")
        return v.lower()

class ReportInput(BaseModel):
    """Input data for generating a report."""
    batch_id: str = Field(..., description="Unique batch identifier")
    violations: List[ViolationEvidence] = Field(..., description="List of violations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

# ------------------------------------------------------------------------------
# ReportGenerator Class
# ------------------------------------------------------------------------------
class ReportGenerator:
    """
    Generates professional PDF forensic reports with visual evidence and legal context.
    Uses ReportLab to produce multi-column, legally defensible documents.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize the ReportGenerator.

        Args:
            config: ReportConfig instance; if None, uses defaults.
        """
        self.config = config or ReportConfig()
        self.temp_files = []  # Track temporary files for cleanup

        # Get page size
        if self.config.page_size == 'letter':
            self.pagesize = letter
        else:
            self.pagesize = A4

        # Style sheet
        self.styles = getSampleStyleSheet()
        self._define_custom_styles()

        logger.info(f"ReportGenerator initialized with output_dir={self.config.output_dir}")

    def _define_custom_styles(self) -> None:
        """Define custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.darkblue,
        ))
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.grey,
        ))
        self.styles.add(ParagraphStyle(
            name='ViolationHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.darkred,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name='ViolationText',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ))
        self.styles.add(ParagraphStyle(
            name='ViolationCode',
            parent=self.styles['Code'],
            fontSize=10,
            textColor=colors.darkgreen,
            backColor=colors.lightgrey,
            leftIndent=10,
            rightIndent=10,
        ))

    def _get_page_size(self) -> Tuple[float, float]:
        """Return page width and height in points."""
        return self.pagesize[0], self.pagesize[1]

    def _resize_image(self, image_path: str) -> str:
        """
        Resize an image to fit within max_evidence_width/height_inches.
        Returns the path to the resized image (temporary file if needed).
        If no resizing is needed, returns the original path.
        """
        img = Image.open(image_path)
        original_width, original_height = img.size
        # Convert inches to pixels (assuming 72 DPI, but we'll use the image's DPI if available)
        dpi = getattr(img, 'dpi', (72, 72))[0] or 72
        max_width_px = int(self.config.max_evidence_width_inches * dpi)
        max_height_px = int(self.config.max_evidence_height_inches * dpi)

        # If the image already fits, return original path
        if original_width <= max_width_px and original_height <= max_height_px:
            return image_path

        # Compute scaling factor
        scale = min(max_width_px / original_width, max_height_px / original_height, 1.0)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        # Resize and save to a temporary file
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img_resized.save(temp_img.name, 'PNG')
        self.temp_files.append(temp_img.name)  # track for cleanup
        temp_img.close()
        return temp_img.name

    def _build_cover_page(self) -> List:
        """
        Build the cover page flowables.
        """
        flowables = []
        # Title
        flowables.append(Paragraph(self.config.title, self.styles['CoverTitle']))
        flowables.append(Spacer(1, 12))
        # Subtitle with batch ID and date
        current_date = datetime.utcnow().strftime("%B %d, %Y")
        flowables.append(Paragraph(f"Inspection Report - {current_date}", self.styles['CoverSubtitle']))
        flowables.append(Spacer(1, 12))
        flowables.append(Paragraph(f"Batch ID: {getattr(self, '_batch_id', 'Unknown')}", self.styles['CoverSubtitle']))
        flowables.append(Spacer(1, 24))
        # Logo if provided
        if self.config.logo_path and os.path.isfile(self.config.logo_path):
            try:
                logo = RLImage(self.config.logo_path, width=2*inch, height=1*inch)
                flowables.append(logo)
                flowables.append(Spacer(1, 12))
            except Exception as e:
                logger.warning(f"Could not load logo: {e}")
        # Metadata summary
        if hasattr(self, '_metadata'):
            flowables.append(Paragraph("Report Metadata:", self.styles['Heading4']))
            for key, value in self._metadata.items():
                flowables.append(Paragraph(f"<b>{key}:</b> {value}", self.styles['Normal']))
                flowables.append(Spacer(1, 4))
        # Separator
        flowables.append(Spacer(1, 24))
        flowables.append(Paragraph("-" * 80, self.styles['Normal']))
        flowables.append(Spacer(1, 12))
        return flowables

    def _build_summary_table(self, violations: List[ViolationEvidence]) -> Table:
        """
        Build a summary table of all violations.
        """
        data = [["#", "Page", "Code", "Description", "Confidence"]]
        for idx, v in enumerate(violations, 1):
            desc_short = v.description[:50] + "..." if len(v.description) > 50 else v.description
            data.append([
                str(idx),
                str(v.page_number),
                v.code_identifier,
                desc_short,
                f"{v.confidence:.2f}"
            ])
        # Create table
        table = Table(data, colWidths=[0.4*inch, 0.6*inch, 1.2*inch, 3*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        return table

    def _build_violation_page(self, violation: ViolationEvidence, idx: int) -> List:
        """
        Build the flowables for a single violation, typically placed on a page.
        Layout: left column (image), right column (details).
        We'll use a table with two columns.
        """
        flowables = []

        # Header
        header_text = f"Violation #{idx}: {violation.code_identifier}"
        flowables.append(Paragraph(header_text, self.styles['ViolationHeader']))
        flowables.append(Spacer(1, 6))

        # Resize evidence image
        try:
            img_path = self._resize_image(violation.evidence_image_path)
            # Image dimensions in points (1 inch = 72 points)
            # We'll set max width to 3.5 inches, height proportional
            max_width = self.config.max_evidence_width_inches * 72
            img = RLImage(img_path, width=max_width, height=None)  # height auto
            # Ensure height doesn't exceed max
            if img.drawHeight > (self.config.max_evidence_height_inches * 72):
                img.drawHeight = self.config.max_evidence_height_inches * 72
                img.drawWidth = max_width  # maintain proportion? We'll let it scale.
        except Exception as e:
            logger.error(f"Failed to load evidence image for {violation.code_identifier}: {e}")
            img = Paragraph("<i>Evidence image not available</i>", self.styles['Normal'])

        # Build right column details
        details = []
        details.append(Paragraph(f"<b>Description:</b> {violation.description}", self.styles['ViolationText']))
        if violation.legal_reference:
            details.append(Paragraph(f"<b>Legal Reference:</b> {violation.legal_reference}", self.styles['ViolationText']))
        details.append(Paragraph(f"<b>Page:</b> {violation.page_number}", self.styles['ViolationText']))
        details.append(Paragraph(f"<b>Confidence:</b> {violation.confidence:.2f}", self.styles['ViolationText']))
        details.append(Paragraph(f"<b>Coordinates:</b> {violation.coordinates}", self.styles['ViolationText']))

        # Build a two-column table: left = image, right = details
        table_data = [
            [img, Paragraph("".join([p.get_xml() for p in details]), self.styles['Normal'])]
        ]
        col_widths = [3.5*inch, 4*inch]  # adjust for letter size
        tbl = Table(table_data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        flowables.append(tbl)
        flowables.append(Spacer(1, 12))

        # Add a horizontal line separator
        flowables.append(Paragraph("_" * 80, self.styles['Normal']))
        flowables.append(Spacer(1, 6))

        return flowables

    async def generate_report(self, input_data: ReportInput) -> Path:
        """
        Generate a forensic PDF report from the input data.

        Args:
            input_data: ReportInput containing violations and metadata.

        Returns:
            Path to the generated PDF file.
        """
        self._batch_id = input_data.batch_id
        self._metadata = input_data.metadata

        # If no violations, create a minimal report
        violations = input_data.violations
        if not violations:
            logger.warning("No violations provided. Generating an empty report.")
            # Still generate a report with a note
            empty_violation = ViolationEvidence(
                page_number=0,
                evidence_image_path="",
                code_identifier="None",
                description="No violations found.",
                legal_reference=None,
                confidence=0.0,
                coordinates=(0,0,0,0)
            )
            # We'll handle later

        # Prepare output file path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"CAIS_Report_{input_data.batch_id}_{timestamp}.pdf"
        output_path = Path(self.config.output_dir) / filename

        # Build document using SimpleDocTemplate
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.pagesize,
            title=self.config.title,
            author=self.config.author,
            subject=f"CAIS Forensic Report - {input_data.batch_id}",
        )

        # Build story (flowables)
        story = []

        # 1. Cover page
        story.extend(self._build_cover_page())

        # 2. Summary Table (if configured)
        if self.config.include_summary_table and violations:
            story.append(Paragraph("Summary of Violations", self.styles['Heading2']))
            story.append(Spacer(1, 6))
            summary_table = self._build_summary_table(violations)
            story.append(summary_table)
            story.append(PageBreak())

        # 3. Individual violation pages
        for idx, v in enumerate(violations, 1):
            story.extend(self._build_violation_page(v, idx))
            # Add page break after each violation except the last
            if idx < len(violations):
                story.append(PageBreak())

        # 4. Build the PDF
        doc.build(story)

        # Cleanup temporary files (resized images)
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
                logger.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not remove temporary file {temp_file}: {e}")
        self.temp_files.clear()

        logger.info(f"Report generated successfully: {output_path}")
        return output_path

    async def generate_report_from_data(
        self,
        batch_id: str,
        violations_data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Convenience method to generate a report from a list of violation dictionaries.

        Args:
            batch_id: Unique batch identifier.
            violations_data: List of dicts with keys matching ViolationEvidence fields.
            metadata: Optional metadata.

        Returns:
            Path to the generated PDF.
        """
        violations = [ViolationEvidence(**v) for v in violations_data]
        input_data = ReportInput(batch_id=batch_id, violations=violations, metadata=metadata or {})
        return await self.generate_report(input_data)

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    import sys
    import random
    logging.basicConfig(level=logging.INFO)

    # Create dummy violation data for testing
    dummy_violations = []
    for i in range(3):
        # We need to have some dummy images; we'll create a small PNG in temp.
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (200, 200), color=(255, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Violation {i}", fill='white')
        img.save(temp_img.name, 'PNG')
        temp_img.close()

        dummy_violations.append({
            "page_number": i+1,
            "evidence_image_path": temp_img.name,
            "code_identifier": f"IBC 1006.2.1-{i}",
            "description": f"Door width less than 32 inches (found {28+i} inches)",
            "legal_reference": "IBC 1006.2.1: Egress doors shall have a minimum clear width of 32 inches.",
            "confidence": 0.85,
            "coordinates": (50, 100, 250, 300)
        })

    # Generate report
    generator = ReportGenerator(ReportConfig(output_dir="./reports"))
    async def main():
        path = await generator.generate_report_from_data(
            batch_id="TEST_001",
            violations_data=dummy_violations,
            metadata={"Inspector": "John Doe", "Client": "CAIS Corp"}
        )
        print(f"Report generated: {path}")
        # Cleanup dummy images
        for v in dummy_violations:
            if os.path.exists(v["evidence_image_path"]):
                os.unlink(v["evidence_image_path"])

    asyncio.run(main())
