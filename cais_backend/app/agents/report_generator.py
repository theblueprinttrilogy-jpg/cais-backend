"""
ReportGenerator Agent - Forensic Facts Dossier Creation

This agent generates the Forensic Facts Dossier with:
- 4-column evidence table (screenshots only)
- No CAIS opinions or reports
- Legal disclaimer
- Professional PDF format

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 6.1
"""

import logging
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

from app.agents.base_agent import BaseAgent
from app.core.database import SessionLocal
from app.db.models import Violation, Document

logger = logging.getLogger(__name__)


class ReportGenerator(BaseAgent):
    """
    ReportGenerator Agent - Forensic Facts Dossier

    Responsibilities:
    1. Create 4-column evidence table
    2. Insert screenshots with red rectangles
    3. Insert code screenshots with yellow highlighting
    4. Add legal disclaimer
    5. Generate professional PDF
    6. No CAIS commentary or opinions
    """

    def __init__(self):
        super().__init__("ReportGenerator", "pdf_generator")
        self.dossier_dir = Path("/tmp/cais_dossiers")
        self.dossier_dir.mkdir(parents=True, exist_ok=True)

    def analyze(self, document: Document) -> Dict[str, Any]:
        """
        Implementation of the abstract analyze method from BaseAgent.

        Args:
            document: Document object containing the analysis results

        Returns:
            dict: Result with status and dossier path
        """
        logger.info(f"ReportGenerator analyzing document: {document.id}")

        # Get violations from database
        db = SessionLocal()
        try:
            violations_db = db.query(Violation).filter(
                Violation.document_id == document.id
            ).all()

            # Prepare violations for report generation
            violations_for_report = []
            for v in violations_db:
                violations_for_report.append({
                    'id': str(v.id),
                    'type': v.violation_type,
                    'severity': v.severity,
                    'description': v.description,
                    'code_reference': v.code_reference,
                    'evidence_path': v.evidence_path,
                    'page_num': v.page_num,
                    'code_evidence_paths': []  # Will be populated if we have code screenshots
                })

            # Generate dossier
            dossier_path = self.generate_dossier(
                violations_for_report,
                document.language or 'en'
            )

            # Update report record in DB if exists
            from app.db.models import Report
            report = db.query(Report).filter(Report.document_id == document.id).first()
            if report:
                report.file_path = dossier_path
                report.generated_at = datetime.utcnow()
                db.commit()
            else:
                # Create new report record
                report = Report(
                    document_id=document.id,
                    file_path=dossier_path,
                    language=document.language or 'en',
                    download_count=0
                )
                db.add(report)
                db.commit()

            return {
                'status': 'completed',
                'dossier_path': dossier_path,
                'violations_count': len(violations_for_report),
                'document_id': str(document.id)
            }

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'document_id': str(document.id)
            }
        finally:
            db.close()

    def generate_dossier(self, violations: List[Dict[str, Any]], document_language: str) -> str:
        """
        Generate a Forensic Facts Dossier PDF.

        Args:
            violations: List of violations with evidence
            document_language: Language for the dossier

        Returns:
            str: Path to the generated PDF
        """
        logger.info(f"Generating Forensic Facts Dossier in {document_language}")

        # Create dossier filename
        dossier_id = uuid.uuid4().hex[:8]
        dossier_path = self.dossier_dir / f"forensic_dossier_{dossier_id}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(
            str(dossier_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        story = []

        # Add title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=30
        )

        title = Paragraph("FORENSIC FACTS DOSSIER", title_style)
        story.append(title)

        # Add subtitle
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=30
        )

        subtitle = Paragraph(
            f"Generated by CAIS Code Compliance | Version 10.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            subtitle_style
        )
        story.append(subtitle)
        story.append(Spacer(1, 20))

        # Check if there are violations
        if not violations:
            # Add a message if no violations found
            no_violations_style = ParagraphStyle(
                'NoViolations',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.green,
                alignment=TA_CENTER,
                spaceAfter=20
            )
            story.append(Paragraph("No code violations detected in this document.", no_violations_style))
        else:
            # Add violation evidence tables
            for i, violation in enumerate(violations):
                # Add violation header
                header_style = ParagraphStyle(
                    f'ViolationHeader_{i}',
                    parent=styles['Heading2'],
                    fontSize=16,
                    textColor=colors.darkred,
                    spaceBefore=20,
                    spaceAfter=10
                )

                header = Paragraph(
                    f"Violation #{i+1}: {violation.get('type', 'Unknown').upper()}",
                    header_style
                )
                story.append(header)

                # Create 4-column evidence table
                evidence_table = self._create_evidence_table(violation)
                story.append(evidence_table)

                story.append(Spacer(1, 20))

        # Add legal disclaimer
        story.append(Spacer(1, 30))
        disclaimer = self._create_legal_disclaimer(document_language)
        story.append(disclaimer)

        # Build PDF
        doc.build(story)

        logger.info(f"Dossier generated: {dossier_path}")
        return str(dossier_path)

    def _create_evidence_table(self, violation: Dict[str, Any]) -> Table:
        """
        Create a 4-column evidence table.

        Columns:
        1: Screenshot of violation with red rectangle
        2-4: Screenshots of codes with yellow highlighting
        """
        # Get evidence paths
        evidence_path = violation.get('evidence_path', '')
        code_evidence_paths = violation.get('code_evidence_paths', [])

        # Ensure we have at least 4 columns
        while len(code_evidence_paths) < 3:
            code_evidence_paths.append('')

        # Create table data
        data = []

        # Add column headers
        headers = [
            "VIOLATION EVIDENCE",
            "CODE REFERENCE 1",
            "CODE REFERENCE 2",
            "CODE REFERENCE 3"
        ]
        data.append(headers)

        # Add images
        row = []

        # Column 1: Violation screenshot
        if evidence_path and os.path.exists(evidence_path):
            try:
                img = Image(evidence_path, width=2.5*inch, height=2*inch)
                row.append(img)
            except Exception as e:
                logger.warning(f"Could not load evidence image: {e}")
                row.append(Paragraph("Evidence image not available", getSampleStyleSheet()['Normal']))
        else:
            row.append(Paragraph("No evidence available", getSampleStyleSheet()['Normal']))

        # Columns 2-4: Code screenshots
        for i in range(3):
            if i < len(code_evidence_paths) and code_evidence_paths[i] and os.path.exists(code_evidence_paths[i]):
                try:
                    img = Image(code_evidence_paths[i], width=2.5*inch, height=2*inch)
                    row.append(img)
                except Exception as e:
                    logger.warning(f"Could not load code evidence image: {e}")
                    row.append(Paragraph("Code reference not available", getSampleStyleSheet()['Normal']))
            else:
                row.append(Paragraph("No code reference available", getSampleStyleSheet()['Normal']))

        data.append(row)

        # Create table
        table = Table(data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch, 2.5*inch])

        # Style the table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.darkblue),
        ])

        table.setStyle(style)
        return table

    def _create_legal_disclaimer(self, language: str) -> Paragraph:
        """
        Create legal disclaimer for the dossier.
        """
        styles = getSampleStyleSheet()

        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_LEFT,
            spaceBefore=10,
            spaceAfter=10
        )

        disclaimer_text = """
        <b>LEGAL DISCLAIMER</b><br/><br/>
        CAIS has 93% of accuracy. CAIS uses an OCR at 200 DPI to scan the documents.
        Some details can be missed based on the document uploaded quality.<br/><br/>
        This Forensic Facts Dossier is generated by CAIS (Construction AI System)
        for informational purposes only.<br/><br/>
        <b>CAIS DOES NOT PROVIDE ANY OPINIONS NOR REPORTS.</b><br/><br/>
        CAIS does not provide legal advice, and this report should not be construed as such.
        All construction decisions should be made in consultation with licensed professionals
        and appropriate regulatory authorities.<br/><br/>
        The visual evidence and code references provided are for reference only and may not
        constitute a complete or accurate representation of all applicable codes, regulations,
        or laws. Users are solely responsible for ensuring compliance with all relevant
        building codes, safety regulations, and legal requirements.<br/><br/>
        CAIS is not liable for any damages, losses, or liabilities arising from the use of
        this report or any actions taken based on its contents.
        """

        return Paragraph(disclaimer_text, disclaimer_style)
