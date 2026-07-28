#!/usr/bin/env python3
"""
ReportGenerator - Forensic dossier PDF with cropped evidence.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ReportGenerator:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("/app/output/dossiers")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_dossier(self, session_id: str, violations: List[Dict], metadata: Optional[Dict] = None) -> Path:
        pdf_path = self.output_dir / f"dossier_{session_id}.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                                rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph("CAIS Forensic Dossier", styles['Title']))
        story.append(Spacer(1, 0.25*inch))
        story.append(Paragraph(f"Session ID: {session_id}", styles['Normal']))
        if metadata:
            if metadata.get('jurisdiction'):
                story.append(Paragraph(f"Jurisdiction: {metadata['jurisdiction']}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        # Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Total violations: {len(violations)}", styles['Normal']))
        story.append(Spacer(1, 0.25*inch))

        if not violations:
            story.append(Paragraph("No violations detected.", styles['Normal']))
        else:
            for i, v in enumerate(violations, 1):
                story.append(PageBreak())
                story.append(Paragraph(f"Violation #{i}: {v.get('type','').replace('_',' ').title()}", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))

                img_path = v.get('screenshot_path', '')
                if img_path and Path(img_path).exists():
                    img = Image(img_path, width=3.5*inch, height=3.5*inch)
                else:
                    img = Paragraph("No image available", styles['Normal'])

                code_text = Paragraph(f"""
                    <b>Code:</b> {v.get('code_reference', '')}<br/>
                    <b>Description:</b> {v.get('code_description', '')}<br/>
                    <b>Detected:</b> {v.get('detected_value', 0)} {v.get('unit', 'in')}<br/>
                    <b>Required:</b> {v.get('required_value', 0)} {v.get('unit', 'in')}<br/>
                    <b>Context:</b> {v.get('context_text', '')[:200]}...
                """, styles['Normal'])

                table_data = [[img, code_text]]
                table = Table(table_data, colWidths=[3.5*inch, 3.0*inch])
                table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN', (0,0), (0,0), 'CENTER'),
                    ('ALIGN', (1,0), (1,0), 'LEFT'),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.15*inch))
                ref = f"Page: {v.get('page_number', '')} | Type: {v.get('type', '')} | Confidence: {v.get('confidence', 'N/A')}"
                story.append(Paragraph(ref, styles['Normal']))
                story.append(Spacer(1, 0.25*inch))

        # Disclaimer
        story.append(PageBreak())
        story.append(Paragraph("Disclaimer", styles['Heading2']))
        story.append(Paragraph(
            "This dossier presents visual evidence of potential code violations. "
            "CAIS does not provide legal advice. All findings should be verified by a qualified professional.",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))

        doc.build(story)
        logger.info(f"Dossier generated: {pdf_path}")
        return pdf_path
