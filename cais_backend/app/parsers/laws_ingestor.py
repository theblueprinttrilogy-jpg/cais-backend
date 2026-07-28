"""
Laws Ingestor - Ingests building codes and regulations from PDFs.
Indexes them for semantic search using embeddings.
"""
import os
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF
import pdfplumber
from datetime import datetime

class LawIngestor:
    """
    Ingests building codes and regulations from PDFs.
    Indexes them for semantic search using embeddings.
    """

    def __init__(self, laws_dir: str = "~/PROMETHEUS/input/laws", output_dir: str = "~/PROMETHEUS/output/laws"):
        self.laws_dir = Path(laws_dir).expanduser()
        self.output_dir = Path(output_dir).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.laws: List[Dict] = []
        self.jurisdictions: Dict[str, List[str]] = {}

    def ingest_all(self) -> Dict[str, Any]:
        """Ingest all laws from the laws directory."""
        if not self.laws_dir.exists():
            self.laws_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created laws directory at: {self.laws_dir}")
            print("Please place building code PDFs in this directory.")
            return {'status': 'no_laws_found'}

        for pdf_path in self.laws_dir.glob("*.pdf"):
            print(f"Ingesting: {pdf_path.name}")
            self._ingest_pdf(pdf_path)

        self._save_ingested_data()
        return {
            'status': 'ingested',
            'total_laws': len(self.laws),
            'jurisdictions': list(self.jurisdictions.keys()),
            'output_dir': str(self.output_dir)
        }

    def _ingest_pdf(self, pdf_path: Path):
        """Ingest a single PDF file."""
        try:
            text = self._extract_text(pdf_path)
            if not text or len(text.strip()) < 100:
                print(f"⚠️ Insufficient text extracted from {pdf_path.name}")
                return

            metadata = self._extract_metadata(pdf_path)
            jurisdiction = self._identify_jurisdiction(text, pdf_path.name)
            sections = self._extract_sections(text)

            with open(pdf_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            law_entry = {
                'id': hashlib.md5(pdf_path.name.encode()).hexdigest(),
                'filename': pdf_path.name,
                'jurisdiction': jurisdiction,
                'metadata': metadata,
                'sections': sections,
                'full_text': text,
                'hash': file_hash,
                'ingested_at': datetime.now().isoformat()
            }

            self.laws.append(law_entry)

            if jurisdiction not in self.jurisdictions:
                self.jurisdictions[jurisdiction] = []
            self.jurisdictions[jurisdiction].append(pdf_path.name)

            print(f"✅ Ingested {pdf_path.name} ({len(sections)} sections)")

        except Exception as e:
            print(f"❌ Error ingesting {pdf_path.name}: {e}")

    def _extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF."""
        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")

        if len(text.strip()) < 500:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e:
                print(f"pdfplumber extraction failed: {e}")

        return text

    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract metadata from PDF."""
        metadata = {}
        try:
            doc = fitz.open(pdf_path)
            if doc.metadata:
                metadata = {
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                }
            doc.close()
        except Exception as e:
            print(f"Metadata extraction failed: {e}")

        metadata['file_size'] = pdf_path.stat().st_size
        metadata['file_modified'] = datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat()
        return metadata

    def _identify_jurisdiction(self, text: str, filename: str) -> str:
        """Identify jurisdiction based on text patterns and filename."""
        text_lower = text.lower()[:5000]

        jurisdiction_patterns = {
            'IBC': ['international building code', 'ibc', 'building code'],
            'NEC': ['national electrical code', 'nec', 'electrical code'],
            'NOM': ['norma oficial mexicana', 'nom-', 'mexican'],
            'ABNT': ['associação brasileira', 'abnt', 'brazilian'],
            'NFPA': ['national fire protection', 'nfpa', 'fire protection'],
            'OSHA': ['occupational safety', 'osha', 'safety regulations'],
            'EUROCODE': ['eurocode', 'european standard'],
            'CBC': ['california building code', 'cbc'],
            'FBC': ['florida building code', 'fbc'],
            'NYCBC': ['new york city building code', 'nyc building'],
        }

        for jurisdiction, patterns in jurisdiction_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return jurisdiction

        filename_lower = filename.lower()
        for jurisdiction, patterns in jurisdiction_patterns.items():
            for pattern in patterns:
                if pattern in filename_lower:
                    return jurisdiction

        return 'Unknown'

    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract sections from law text."""
        sections = []
        section_patterns = [
            r'(Section|Sec|§)\s*(\d+\.?\d*\.?\d*)',
            r'(Chapter|Ch\.)\s*(\d+)',
            r'(Article|Art\.)\s*(\d+)',
        ]

        lines = text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_new_section = False
            section_number = None

            for pattern in section_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    section_number = match.group(0)
                    is_new_section = True
                    break

            if is_new_section and current_section:
                sections.append({
                    'number': current_section,
                    'content': '\n'.join(current_content)[:1000]
                })
                current_section = section_number
                current_content = []
            elif is_new_section:
                current_section = section_number
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        if current_section and current_content:
            sections.append({
                'number': current_section,
                'content': '\n'.join(current_content)[:1000]
            })

        return sections

    def _save_ingested_data(self):
        """Save the ingested laws data."""
        with open(self.output_dir / 'laws_data.json', 'w') as f:
            json.dump(self.laws, f, indent=2, default=str)

        with open(self.output_dir / 'jurisdictions.json', 'w') as f:
            json.dump(self.jurisdictions, f, indent=2)

        summary = {
            'ingested_at': datetime.now().isoformat(),
            'total_laws': len(self.laws),
            'jurisdictions': list(self.jurisdictions.keys()),
            'jurisdiction_counts': {
                j: len(files) for j, files in self.jurisdictions.items()
            }
        }
        with open(self.output_dir / 'ingestion_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n✅ Laws ingestion complete.")
        print(f"   Total laws: {len(self.laws)}")
        print(f"   Jurisdictions: {list(self.jurisdictions.keys())}")
