"""
Dossier Generator for CAIS backend.

Produces a professional Forensic Facts Dossier in PDF format using ReportLab.
The dossier presents each violation with a 4-column evidence table:
1. Cropped blueprint element with a RED rectangular bounding box.
2. Violated building code with YELLOW highlighting (image or text).
3. Violated safety regulation with YELLOW highlighting (image or text).
4. Violated construction law with YELLOW highlighting (image or text).

No subjective opinions or AI editorial comments are included.
Only factual visual evidence and legal citations.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

# Mandatory legal disclaimer text
LEGAL_DISCLAIMER = """
LEGAL DISCLAIMER

This Forensic Facts Dossier has been prepared using automated optical character
recognition (OCR) at 200 DPI and deterministic image analysis. The information
contained herein is provided for informational purposes only and should not be
construed as legal advice, engineering judgment, or a substitute for professional
on-site inspection. The system reports a statistical accuracy of 93% for detected
elements; however, users are solely responsible for verifying all findings,
conducting independent reviews, and ensuring compliance with all applicable laws,
codes, and regulations. The authors, developers, and operators of this system
assume no liability for any errors, omissions, or actions taken based on this
report.
"""


class DossierGenerator:
    """
    Generates a Forensic Facts Dossier PDF using ReportLab.
    """

    def __init__(
        self,
        pagesize: Tuple[float, float] = letter,
        margin: float = 0.75 * inch,
        image_width: float = 1.5 * inch,
        image_height: float = 1.5 * inch,
    ):
        """
        Initialize the dossier generator.

        :param pagesize: Page size (default letter).
        :param margin: Margin around page content.
        :param image_width: Width of cropped evidence images.
        :param image_height: Height of cropped evidence images.
        """
        self.pagesize = pagesize
        self.margin = margin
        self.image_width = image_width
        self.image_height = image_height
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self) -> None:
        """Create custom paragraph styles for the dossier."""
        # Title style
        self.styles.add(
            ParagraphStyle(
                name="DossierTitle",
                parent=self.styles["Heading1"],
                fontSize=20,
                alignment=TA_CENTER,
                spaceAfter=12,
            )
        )
        # Section header
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=6,
                spaceBefore=12,
            )
        )
        # Body text
        self.styles.add(
            ParagraphStyle(
                name="DossierBody",
                parent=self.styles["Normal"],
                fontSize=10,
                alignment=TA_LEFT,
                spaceAfter=4,
            )
        )
        # Disclaimer style
        self.styles.add(
            ParagraphStyle(
                name="Disclaimer",
                parent=self.styles["Normal"],
                fontSize=8,
                alignment=TA_LEFT,
                spaceAfter=12,
                spaceBefore=12,
                italic=True,
            )
        )

    def _safe_image(self, image_path: str) -> Optional[Image]:
        """
        Safely create an Image platypus element from a path.
        Returns None if the file does not exist or cannot be read.

        :param image_path: Path to image file.
        :return: Image object or None.
        """
        if not image_path or not os.path.isfile(image_path):
            logger.warning(f"Image not found: {image_path}")
            return None
        try:
            img = Image(image_path, width=self.image_width, height=self.image_height)
            return img
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return None

    def _build_evidence_table(
        self,
        violation: Dict[str, Any],
    ) -> Table:
        """
        Build a 4-column evidence table for a single violation.

        Columns:
        1. Blueprint element (cropped image with red box)
        2. Building code reference (text or image with yellow highlight)
        3. Safety regulation (text or image with yellow highlight)
        4. Construction law (text or image with yellow highlight)

        :param violation: Dictionary containing evidence data.
        :return: Table platypus element.
        """
        # Column 1: Blueprint image (assumed already cropped with red bounding box)
        blueprint_img = self._safe_image(violation.get("blueprint_image_path", ""))
        col1_content = []
        if blueprint_img:
            col1_content.append(blueprint_img)
        else:
            col1_content.append(Paragraph("No blueprint image", self.styles["DossierBody"]))
        col1_content.append(Paragraph("Blueprint", self.styles["DossierBody"]))

        # Column 2: Code reference (image or text with yellow highlight)
        col2_content = []
        code_img = self._safe_image(violation.get("code_image_path", ""))
        if code_img:
            col2_content.append(code_img)
        else:
            code_text = violation.get("code_reference", "No code reference")
            col2_content.append(
                Paragraph(
                    f"<font color='#FFD700'><b>{code_text}</b></font>",
                    self.styles["DossierBody"],
                )
            )
        col2_content.append(Paragraph("Building Code", self.styles["DossierBody"]))

        # Column 3: Safety regulation (image or text with yellow highlight)
        col3_content = []
        safety_img = self._safe_image(violation.get("safety_image_path", ""))
        if safety_img:
            col3_content.append(safety_img)
        else:
            safety_text = violation.get("safety_reference", "No safety regulation")
            col3_content.append(
                Paragraph(
                    f"<font color='#FFD700'><b>{safety_text}</b></font>",
                    self.styles["DossierBody"],
                )
            )
        col3_content.append(Paragraph("Safety Regulation", self.styles["DossierBody"]))

        # Column 4: Construction law (image or text with yellow highlight)
        col4_content = []
        law_img = self._safe_image(violation.get("law_image_path", ""))
        if law_img:
            col4_content.append(law_img)
        else:
            law_text = violation.get("law_reference", "No construction law")
            col4_content.append(
                Paragraph(
                    f"<font color='#FFD700'><b>{law_text}</b></font>",
                    self.styles["DossierBody"],
                )
            )
        col4_content.append(Paragraph("Construction Law", self.styles["DossierBody"]))

        # Build the table data: one row with 4 cells, each cell is a list of flowables
        data = [[col1_content, col2_content, col3_content, col4_content]]

        # Create table with fixed column widths
        col_widths = [self.image_width + 0.25 * inch] * 4
        table = Table(data, colWidths=col_widths, hAlign="CENTER")

        # Apply table style: borders, padding, background
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.beige),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),  # Fixed: thickness then color
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),  # Correct order
            ]
        )
        table.setStyle(style)
        return table

    def generate_dossier(
        self,
        violations: List[Dict[str, Any]],
        output_path: str,
        title: str = "Forensic Facts Dossier",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate the Forensic Facts Dossier PDF.

        Each violation dict should contain:
            - blueprint_image_path: Path to cropped blueprint image with red box.
            - code_reference: Text of building code violation (or code_image_path).
            - safety_reference: Text of safety regulation violation (or safety_image_path).
            - law_reference: Text of construction law violation (or law_image_path).
        Optionally, provide image paths for columns 2-4:
            - code_image_path
            - safety_image_path
            - law_image_path
        If an image path is provided, it takes precedence over text.

        :param violations: List of violation dictionaries.
        :param output_path: Path where the PDF will be saved.
        :param title: Title of the dossier.
        :param metadata: Additional metadata (e.g., address, date) to include.
        :return: Output path.
        """
        logger.info(f"Generating Forensic Facts Dossier: {output_path}")

        # Create the document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.pagesize,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        # Build the story (content flowables)
        story = []

        # Title
        story.append(Paragraph(title, self.styles["DossierTitle"]))
        story.append(Spacer(1, 0.25 * inch))

        # Metadata
        if metadata:
            meta_text = f"Address: {metadata.get('address', 'N/A')}<br/>Date: {metadata.get('date', datetime.now().strftime('%Y-%m-%d'))}"
            story.append(Paragraph(meta_text, self.styles["DossierBody"]))
            story.append(Spacer(1, 0.15 * inch))

        # Foreword: "This dossier contains factual visual evidence and legal citations."
        foreword = "This dossier contains factual visual evidence and legal citations. "
        foreword += "No subjective opinions or AI editorial comments are included."
        story.append(Paragraph(foreword, self.styles["DossierBody"]))
        story.append(Spacer(1, 0.2 * inch))

        # Process each violation
        if not violations:
            story.append(Paragraph("No violations detected.", self.styles["DossierBody"]))
        else:
            for idx, violation in enumerate(violations, start=1):
                # Section header: Violation #n
                story.append(
                    Paragraph(
                        f"Violation {idx}: {violation.get('title', 'Unnamed')}",
                        self.styles["SectionHeader"]
                    )
                )
                # Evidence table
                table = self._build_evidence_table(violation)
                story.append(table)
                story.append(Spacer(1, 0.1 * inch))

                # Add a page break after each violation except the last
                if idx < len(violations):
                    story.append(PageBreak())

        # Add a page break before the disclaimer
        story.append(PageBreak())
        # Legal disclaimer
        disclaimer_paragraph = Paragraph(LEGAL_DISCLAIMER, self.styles["Disclaimer"])
        story.append(disclaimer_paragraph)

        # Build the PDF
        doc.build(story)
        logger.info(f"Dossier generated successfully: {output_path}")
        return output_path


# Convenience function for one-shot generation
def generate_forensic_dossier(
    violations: List[Dict[str, Any]],
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a Forensic Facts Dossier PDF.

    :param violations: List of violation dictionaries as described above.
    :param output_path: Path to save the PDF.
    :param metadata: Optional metadata dict.
    :return: Output path.
    """
    generator = DossierGenerator()
    return generator.generate_dossier(violations, output_path, metadata=metadata)
