#!/usr/bin/env python3
"""
Clasificador de Códigos de Construcción por Jurisdicción y Severidad.
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import fitz  # PyMuPDF


@dataclass
class CodeSection:
    """Representa una sección de un código de construcción."""
    code_id: str
    jurisdiction: str
    category: str  # 'hurricane', 'seismic', 'general'
    section_number: str
    title: str
    content: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    keywords: List[str]
    hash: str = ""


class CodeClassifier:
    """
    Clasifica códigos de construcción por jurisdicción y severidad.
    """
    
    def __init__(self, laws_dir: str = "~/PROMETHEUS/input/laws"):
        """
        Initialize the code classifier.
        
        Args:
            laws_dir: Directory containing downloaded codes.
        """
        self.laws_dir = Path(laws_dir).expanduser()
        self.classified_sections: List[CodeSection] = []
        
        # Keywords for Florida (Hurricanes)
        self.hurricane_keywords = [
            'hurricane', 'wind', 'storm', 'tornado', 'cyclone',
            'wind speed', 'wind load', 'pressure', 'impact', 'debris',
            'wind-borne debris', 'missile impact', 'roof covering',
            'shutters', 'impact-resistant', 'high-velocity',
            'hurricane zone', 'hurricane shelter', 'wind uplift'
        ]
        
        # Keywords for California (Earthquakes)
        self.seismic_keywords = [
            'earthquake', 'seismic', 'tremor', 'fault', 'ground motion',
            'seismic load', 'lateral force', 'base shear', 'overturning',
            'drift', 'diaphragm', 'shear wall', 'moment frame',
            'braced frame', 'seismic design', 'ductility', 'damping',
            'response spectrum', 'seismic zone', 'seismic risk'
        ]
        
        # Critical sections to identify
        self.critical_patterns = {
            'critical': [
                r'(shall|must|required)\s+.*?minimum',
                r'(shall|must|required)\s+.*?maximum',
                r'not\s+.*?less\s+than',
                r'not\s+.*?exceed',
                r'prohibited|forbidden|not\s+allowed',
                r'emergency|life\s+safety|exit|egress',
                r'structural|load-bearing|foundation|frame',
                r'fire\s+resistance|fire\s+protection',
                r'safety|protection|critical',
            ],
            'high': [
                r'should|recommended|advisable',
                r'best\s+practice|standard\s+practice',
                r'typical|commonly|generally',
                r'consider|consideration|important',
                r'significant|major|substantial',
            ],
            'medium': [
                r'may|optional|permitted|allowed',
                r'alternative|alternate|other\s+options',
                r'unless|except|otherwise',
                r'usually|normally|often',
            ],
            'low': [
                r'suggested|advisory|guideline',
                r'informational|reference|note',
                r'typical|usual|common',
                r'additional\s+information|further\s+detail',
            ]
        }
    
    def classify_all(self) -> Dict[str, Any]:
        """
        Classify all downloaded codes.
        
        Returns:
            Dict with classification results.
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_sections': 0,
            'by_jurisdiction': {},
            'by_category': {},
            'by_severity': {},
            'sections': []
        }
        
        # Process each PDF
        for pdf_path in self.laws_dir.glob("*.pdf"):
            print(f"📖 Classifying: {pdf_path.name}")
            sections = self._classify_pdf(pdf_path)
            
            for section in sections:
                self.classified_sections.append(section)
                
                # Update counts
                results['total_sections'] += 1
                
                if section.jurisdiction not in results['by_jurisdiction']:
                    results['by_jurisdiction'][section.jurisdiction] = 0
                results['by_jurisdiction'][section.jurisdiction] += 1
                
                if section.category not in results['by_category']:
                    results['by_category'][section.category] = 0
                results['by_category'][section.category] += 1
                
                if section.severity not in results['by_severity']:
                    results['by_severity'][section.severity] = 0
                results['by_severity'][section.severity] += 1
                
                results['sections'].append({
                    'code_id': section.code_id,
                    'jurisdiction': section.jurisdiction,
                    'category': section.category,
                    'section_number': section.section_number,
                    'title': section.title,
                    'content': section.content[:500] + '...',
                    'severity': section.severity,
                    'keywords': section.keywords[:10]
                })
        
        # Save results
        output_path = Path("~/PROMETHEUS/output/classified_codes.json").expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Classification complete!")
        print(f"  Total sections: {results['total_sections']}")
        print(f"  Jurisdictions: {list(results['by_jurisdiction'].keys())}")
        print(f"  Categories: {list(results['by_category'].keys())}")
        
        return results
    
    def _classify_pdf(self, pdf_path: Path) -> List[CodeSection]:
        """
        Classify a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            List of classified code sections.
        """
        sections = []
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text:
                    full_text += text + "\n"
            
            doc.close()
            
            # If no text extracted, try pdfplumber as fallback
            if len(full_text.strip()) < 100:
                try:
                    import pdfplumber
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n"
                except ImportError:
                    pass
            
            if len(full_text.strip()) < 50:
                print(f"  ⚠️ No text extracted from {pdf_path.name}")
                return sections
            
            # Determine jurisdiction from filename
            jurisdiction = self._detect_jurisdiction(pdf_path.name)
            category = self._detect_category(full_text, jurisdiction)
            
            # Extract sections
            raw_sections = self._extract_sections(full_text)
            
            if not raw_sections:
                # If no sections found, create one section with the full text
                print(f"  ⚠️ No sections found in {pdf_path.name}, creating single section")
                raw_sections = [("1.0", "Full Document", full_text[:5000])]
            
            for i, (section_num, section_title, content) in enumerate(raw_sections):
                if len(content.strip()) < 20:
                    continue
                
                # Determine severity
                severity = self._determine_severity(content)
                
                # Extract keywords
                keywords = self._extract_keywords(content, category)
                
                # Generate code ID
                clean_section = re.sub(r'[^a-zA-Z0-9_]', '_', section_num[:20])
                code_id = f"{jurisdiction}_{category}_{clean_section}"
                
                # Calculate hash
                section_hash = hashlib.sha256(content.encode()).hexdigest()
                
                sections.append(CodeSection(
                    code_id=code_id,
                    jurisdiction=jurisdiction,
                    category=category,
                    section_number=section_num[:30],
                    title=section_title[:100] if section_title else f"Section {section_num}",
                    content=content[:2000],
                    severity=severity,
                    keywords=keywords[:20],
                    hash=section_hash
                ))
            
            print(f"  ✅ Extracted {len(sections)} sections from {pdf_path.name}")
            
        except Exception as e:
            print(f"  ❌ Error classifying {pdf_path.name}: {e}")
        
        return sections
    
    def _detect_jurisdiction(self, filename: str) -> str:
        """Detect jurisdiction from filename."""
        filename_lower = filename.lower()
        
        if 'florida' in filename_lower or 'fbc' in filename_lower:
            return 'Florida'
        elif 'miami' in filename_lower or 'dade' in filename_lower:
            return 'Florida-MiamiDade'
        elif 'california' in filename_lower or 'cbc' in filename_lower:
            return 'California'
        elif 'asce' in filename_lower:
            return 'National'
        elif 'ibc' in filename_lower:
            return 'International'
        elif 'nfpa' in filename_lower:
            return 'National'
        else:
            return 'Unknown'
    
    def _detect_category(self, text: str, jurisdiction: str) -> str:
        """Detect category based on content and jurisdiction."""
        text_lower = text.lower()
        
        # Check for hurricane keywords
        for keyword in self.hurricane_keywords:
            if keyword in text_lower:
                return 'hurricane'
        
        # Check for seismic keywords
        for keyword in self.seismic_keywords:
            if keyword in text_lower:
                return 'seismic'
        
        # Jurisdiction-based defaults
        if jurisdiction == 'Florida':
            return 'hurricane'
        elif jurisdiction == 'California':
            return 'seismic'
        else:
            return 'general'
    
    def _extract_sections(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract code sections from text.
        
        Returns:
            List of (section_number, section_title, content) tuples.
        """
        sections = []
        
        # More flexible section patterns
        section_patterns = [
            # Section with number and title
            r'(?:Section|Sec\.|§)\s*(\d+\.?\d*\.?\d*)\s*[-–:]\s*([^\n]+)',
            r'(?:Section|Sec\.|§)\s*(\d+\.?\d*\.?\d*)\s*([A-Z][^\n]+)',
            # Just a number with title
            r'^(\d+\.?\d*\.?\d*)\s+([A-Z][^\n]+)',
            # Chapter pattern
            r'(?:Chapter|Ch\.)\s*(\d+)\s*[-–:]\s*([^\n]+)',
            # Article pattern
            r'(?:Article|Art\.)\s*(\d+\.?\d*)\s*[-–:]\s*([^\n]+)',
            # Numbered sections (1.0, 1.1, etc.)
            r'^(\d+\.\d+)\s+([A-Z][^\n]+)',
        ]
        
        lines = text.split('\n')
        current_section = None
        current_title = ""
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header
            is_section = False
            section_num = ""
            section_title = ""
            
            for pattern in section_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Try to identify which group is the number and which is the title
                        if re.match(r'^[\d\.]+$', groups[0]):
                            section_num = groups[0]
                            section_title = groups[1].strip()
                        elif re.match(r'^[\d\.]+$', groups[1]):
                            section_num = groups[1]
                            section_title = groups[0].strip()
                        else:
                            # Use first as number if it looks like one
                            if re.match(r'^[\d\.]+$', groups[0]):
                                section_num = groups[0]
                                section_title = groups[1].strip()
                            else:
                                section_num = groups[1]
                                section_title = groups[0].strip()
                        is_section = True
                        break
                    elif len(groups) == 1:
                        # Try to parse as section number
                        if re.match(r'^[\d\.]+$', groups[0]):
                            section_num = groups[0]
                            section_title = f"Section {section_num}"
                            is_section = True
                            break
            
            if is_section:
                # Save previous section
                if current_section and current_content:
                    sections.append((
                        current_section,
                        current_title,
                        '\n'.join(current_content)
                    ))
                
                current_section = section_num
                current_title = section_title[:200] if section_title else f"Section {section_num}"
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Save last section
        if current_section and current_content:
            sections.append((
                current_section,
                current_title,
                '\n'.join(current_content)
            ))
        
        # If no sections found, create a single section with all text
        if not sections and text.strip():
            sections.append((
                "1.0",
                "Full Document",
                text[:5000]
            ))
        
        return sections
    
    def _determine_severity(self, content: str) -> str:
        """Determine severity of a code section."""
        content_lower = content.lower()
        
        # Check for critical patterns
        for severity, patterns in self.critical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return severity
        
        # Default severity based on content length
        if len(content) > 500:
            return 'medium'
        else:
            return 'low'
    
    def _extract_keywords(self, content: str, category: str) -> List[str]:
        """Extract keywords from content."""
        keywords = []
        
        # Add category keywords
        if category == 'hurricane':
            keywords.extend(self.hurricane_keywords[:10])
        elif category == 'seismic':
            keywords.extend(self.seismic_keywords[:10])
        
        # Extract technical terms
        technical_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b', content)
        
        for term in technical_terms:
            if len(term) > 3 and term not in keywords:
                keywords.append(term)
        
        return keywords[:30]
