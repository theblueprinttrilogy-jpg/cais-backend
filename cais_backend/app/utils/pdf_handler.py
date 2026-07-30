"""
PDF Handler - PDF Processing Utilities

This module provides utilities for PDF processing.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from io import BytesIO
from PIL import Image


class PDFHandler:
    """
    PDF handler for processing PDF files.
    """

    def __init__(self, dpi: int = 200):
        self.dpi = dpi

    def convert_pdf_to_images(
        self,
        pdf_path: str,
        dpi: Optional[int] = None,
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        Convert PDF to images at specified DPI.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution (default: 200)
            output_dir: Directory to save images

        Returns:
            List of image file paths
        """
        try:
            import pdf2image
        except ImportError:
            raise ImportError("pdf2image is required for PDF processing")

        dpi = dpi or self.dpi
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)

        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        else:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        output_paths = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        for i, img in enumerate(images):
            page_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.png")
            img.save(page_path, "PNG")
            output_paths.append(page_path)

        return output_paths

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from PDF.
        """
        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF (fitz) is required for text extraction")

        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"

        return text

    def extract_text_with_ocr(self, pdf_path: str) -> str:
        """
        Extract text using OCR (for scanned PDFs).
        """
        import pytesseract

        images = self.convert_pdf_to_images(pdf_path)
        text = ""

        for img_path in images:
            img = Image.open(img_path)
            page_text = pytesseract.image_to_string(img, lang="eng+spa")
            text += page_text + "\n"

        return text

    def get_page_count(self, pdf_path: str) -> int:
        """
        Get number of pages in PDF.
        """
        import fitz

        with fitz.open(pdf_path) as doc:
            return len(doc)

    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get PDF metadata.
        """
        import fitz

        with fitz.open(pdf_path) as doc:
            metadata = doc.metadata
            return {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": len(doc),
            }
