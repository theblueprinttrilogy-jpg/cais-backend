#!/usr/bin/env python3
"""
Laws Ingestor - CAIS Autopoietic System
Ingesta de códigos normativos desde múltiples fuentes
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)

@dataclass
class CodeSection:
    """Representa una sección de un código normativo"""
    code_id: str
    section_number: str
    title: str
    content: str
    chapter: Optional[str] = None
    article: Optional[str] = None
    jurisdiction: str = "IBC"
    keywords: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    severity: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class CodeDocument:
    """Representa un documento de código completo"""
    id: str
    title: str
    jurisdiction: str
    year: int
    sections: List[CodeSection]
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingested_at: str = field(default_factory=lambda: datetime.now().isoformat())

class LawsIngestor:
    """
    Ingestor de leyes y códigos normativos.
    Extrae secciones, títulos y contenido de documentos legales.
    """
    
    def __init__(self, input_dir: Path = Path("~/PROMETHEUS/input/laws")):
        self.input_dir = Path(input_dir).expanduser()
        self.output_dir = Path("~/PROMETHEUS/output/laws").expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.codes: Dict[str, CodeDocument] = {}
        self.sections: List[CodeSection] = []
        
        # Patrones para extraer secciones
        self.section_patterns = [
            r'(?:Section|Sec\.|§)\s*(\d+\.?\d*\.?\d*)',
            r'(?:Article|Art\.|A\.)\s*(\d+\.?\d*\.?\d*)',
            r'(?:Chapter|Ch\.|C\.)\s*(\d+\.?\d*\.?\d*)',
        ]
        
        # Patrones para títulos
        self.title_patterns = [
            r'([A-Z][A-Z\s]+)\s*(?:Section|Sec\.|§)\s*\d+',
            r'([A-Z][A-Z\s]+)\.?\s*\d+\.?\d*',
        ]
        
        logger.info(f"LawsIngestor initialized with input: {self.input_dir}")
    
    def ingest_pdf(self, pdf_path: Path) -> CodeDocument:
        """
        Ingiere un PDF de código normativo.
        Extrae secciones y contenido estructurado.
        """
        logger.info(f"📄 Ingesting: {pdf_path.name}")
        
        sections = []
        current_section = None
        current_content = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"
                
                # Extraer metadatos básicos
                metadata = self._extract_metadata(pdf_path, full_text)
                
                # Dividir en secciones
                lines = full_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Detectar nueva sección
                    section_match = self._detect_section(line)
                    if section_match:
                        # Guardar sección anterior
                        if current_section:
                            current_section.content = '\n'.join(current_content).strip()
                            sections.append(current_section)
                            current_content = []
                        
                        # Crear nueva sección
                        section_number, title = section_match
                        current_section = CodeSection(
                            code_id=pdf_path.stem,
                            section_number=section_number,
                            title=title or f"Section {section_number}",
                            content="",
                            jurisdiction=metadata.get('jurisdiction', 'IBC')
                        )
                    else:
                        # Añadir contenido a la sección actual
                        if current_section:
                            current_content.append(line)
                
                # Guardar última sección
                if current_section and current_content:
                    current_section.content = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Extraer keywords
                for section in sections:
                    section.keywords = self._extract_keywords(section.content)
                    section.references = self._extract_references(section.content)
            
            # Crear documento
            doc = CodeDocument(
                id=pdf_path.stem,
                title=metadata.get('title', pdf_path.stem),
                jurisdiction=metadata.get('jurisdiction', 'IBC'),
                year=metadata.get('year', datetime.now().year),
                sections=sections,
                metadata=metadata
            )
            
            self.codes[doc.id] = doc
            self.sections.extend(sections)
            
            logger.info(f"✅ Ingested {len(sections)} sections from {pdf_path.name}")
            return doc
            
        except Exception as e:
            logger.error(f"❌ Error ingesting {pdf_path.name}: {e}")
            return None
    
    def ingest_all_pdfs(self) -> Dict[str, CodeDocument]:
        """Ingiere todos los PDFs en el directorio de entrada"""
        results = {}
        
        for pdf_path in self.input_dir.glob("*.pdf"):
            doc = self.ingest_pdf(pdf_path)
            if doc:
                results[doc.id] = doc
        
        # Guardar resultados
        self._save_results()
        
        return results
    
    def _extract_metadata(self, pdf_path: Path, text: str) -> Dict[str, Any]:
        """Extrae metadatos del documento"""
        metadata = {
            'title': pdf_path.stem,
            'jurisdiction': 'IBC',
            'year': datetime.now().year,
            'source': str(pdf_path)
        }
        
        # Intentar extraer año
        year_match = re.search(r'(20\d{2})', text[:500])
        if year_match:
            metadata['year'] = int(year_match.group(1))
        
        # Intentar extraer jurisdicción
        jurisdictions = ['IBC', 'NFPA', 'OSHA', 'ADA', 'NEC', 'CBC', 'FBC']
        for jur in jurisdictions:
            if jur in text[:1000]:
                metadata['jurisdiction'] = jur
                break
        
        return metadata
    
    def _detect_section(self, line: str) -> Optional[Tuple[str, str]]:
        """Detecta si una línea es una sección"""
        for pattern in self.section_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                section_num = match.group(1)
                # Intentar extraer título
                title = None
                for title_pattern in self.title_patterns:
                    title_match = re.search(title_pattern, line, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                        break
                
                return (section_num, title)
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrae palabras clave del texto"""
        # Palabras clave comunes en códigos de construcción
        common_terms = [
            'building', 'construction', 'safety', 'fire', 'structural',
            'electrical', 'plumbing', 'mechanical', 'energy', 'accessibility',
            'foundation', 'roof', 'wall', 'floor', 'ceiling', 'door', 'window',
            'stair', 'elevator', 'exit', 'emergency', 'alarm', 'sprinkler',
            'compliance', 'permit', 'inspection', 'occupancy', 'zoning'
        ]
        
        text_lower = text.lower()
        keywords = [term for term in common_terms if term in text_lower]
        return keywords[:10]  # Limit to top 10
    
    def _extract_references(self, text: str) -> List[str]:
        """Extrae referencias a otras secciones"""
        references = []
        # Buscar referencias como "Section X", "Sec. X", "§ X"
        ref_pattern = r'(?:Section|Sec\.|§)\s*(\d+\.?\d*\.?\d*)'
        matches = re.findall(ref_pattern, text, re.IGNORECASE)
        references.extend(matches)
        return list(set(references))[:10]  # Limit to top 10
    
    def _save_results(self):
        """Guarda los resultados de la ingesta"""
        # Guardar código completo
        for code_id, doc in self.codes.items():
            code_path = self.output_dir / f"{code_id}_full.json"
            code_data = {
                'id': doc.id,
                'title': doc.title,
                'jurisdiction': doc.jurisdiction,
                'year': doc.year,
                'metadata': doc.metadata,
                'sections': [
                    {
                        'section_number': s.section_number,
                        'title': s.title,
                        'content': s.content[:500] + '...' if len(s.content) > 500 else s.content,
                        'keywords': s.keywords,
                        'references': s.references,
                        'severity': s.severity
                    }
                    for s in doc.sections
                ],
                'ingested_at': doc.ingested_at
            }
            code_path.write_text(json.dumps(code_data, indent=2, default=str))
            logger.info(f"📁 Saved: {code_path}")
        
        # Guardar todas las secciones
        sections_path = self.output_dir / "all_sections.json"
        sections_data = [
            {
                'code_id': s.code_id,
                'section_number': s.section_number,
                'title': s.title,
                'content': s.content[:500] + '...' if len(s.content) > 500 else s.content,
                'jurisdiction': s.jurisdiction,
                'keywords': s.keywords,
                'references': s.references,
                'severity': s.severity,
                'created_at': s.created_at
            }
            for s in self.sections
        ]
        sections_path.write_text(json.dumps(sections_data, indent=2, default=str))
        logger.info(f"📁 Saved: {sections_path} (total: {len(self.sections)} sections)")
        
        # Guardar resumen
        summary_path = self.output_dir / "ingestion_summary.json"
        summary = {
            'total_codes': len(self.codes),
            'total_sections': len(self.sections),
            'codes': list(self.codes.keys()),
            'jurisdictions': list(set(s.jurisdiction for s in self.sections)),
            'ingested_at': datetime.now().isoformat()
        }
        summary_path.write_text(json.dumps(summary, indent=2))
        logger.info(f"📁 Saved: {summary_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la ingesta"""
        return {
            'total_codes': len(self.codes),
            'total_sections': len(self.sections),
            'jurisdictions': list(set(s.jurisdiction for s in self.sections)),
            'avg_sections_per_code': len(self.sections) / len(self.codes) if self.codes else 0,
            'total_keywords': sum(len(s.keywords) for s in self.sections),
            'total_references': sum(len(s.references) for s in self.sections)
        }


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     📜 LAWS INGESTOR - CAIS AUTOPOIETIC SYSTEM           ║
║                                                           ║
║     Ingiriendo códigos normativos...                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    ingestor = LawsIngestor()
    results = ingestor.ingest_all_pdfs()
    
    stats = ingestor.get_stats()
    print("\n" + "="*60)
    print("📊 INGESTION COMPLETE")
    print("="*60)
    print(f"   Total Codes: {stats['total_codes']}")
    print(f"   Total Sections: {stats['total_sections']}")
    print(f"   Jurisdictions: {', '.join(stats['jurisdictions'])}")
    print(f"   Avg Sections per Code: {stats['avg_sections_per_code']:.1f}")
    print("="*60)
    print(f"\n📁 Output: {ingestor.output_dir}")
