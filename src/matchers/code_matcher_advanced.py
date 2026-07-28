#!/usr/bin/env python3
"""
CodeMatcher Advanced - TASK 24 - COMPLETE VERSION WITH SEMANTIC FILTER
Intelligent semantic code matching with multi-language support.
Uses compiled semantic filter from construction codes, regulations, and laws.
Detects violations and generates visual evidence.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import sys
import json
import re
import asyncio
import asyncpg
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Semantic Search
from sentence_transformers import SentenceTransformer

# Language detection
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

# Import semantic dictionary
from src.dictionaries.semantic_dictionary import SemanticDictionaryManager

# Import semantic filter compiler
from src.matchers.semantic_filter_compiler import SemanticFilterCompiler

# PDF Processing
from pdf2image import convert_from_path
import fitz


@dataclass
class ViolationEvidence:
    """Evidence of a violation with visual proof."""
    violation_id: str
    code_id: str
    severity: str
    similarity_score: float
    document_text: str
    code_text: str
    page_number: int
    screenshot_path: str
    code_highlight_path: str
    matched_terms: List[str]
    language: str
    confidence: float
    term_matches: List[Dict] = field(default_factory=list)


@dataclass
class MatchResult:
    """Result from code matching."""
    code_id: str
    code_content: str
    jurisdiction: str
    severity: str
    similarity_score: float
    matched_text: str
    context: str
    confidence: float
    match_type: str
    page_number: int
    matched_terms: List[str] = field(default_factory=list)
    term_match_details: List[Dict] = field(default_factory=list)
    evidence: Optional[ViolationEvidence] = None


class CodeMatcherAdvanced:
    """
    TASK 24: CodeMatcher Advanced - COMPLETE INTELLIGENT VERSION
    
    Features:
    - Multi-language detection and semantic dictionaries
    - Semantic filter compiled from ALL codes, regulations, and laws
    - Intelligent violation detection with term matching
    - Visual evidence generation (RED boxes + YELLOW highlights)
    - Confidence scoring with detailed explanation
    """
    
    # Similarity thresholds
    THRESHOLDS = {
        'critical': 0.85,
        'high': 0.75,
        'medium': 0.65,
        'low': 0.55
    }
    
    def __init__(self, db_config: Optional[Dict] = None, evidence_dir: str = "./evidence"):
        """
        Initialize the advanced CodeMatcher.
        
        Args:
            db_config: Database configuration
            evidence_dir: Directory for evidence output
        """
        self.db_config = db_config or {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        self.evidence_dir = Path(evidence_dir).expanduser()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Load embedding model
        print("📥 Loading embedding model...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"   ✅ Model loaded: {self.model.get_sentence_embedding_dimension()} dimensions")
        
        # Initialize semantic dictionary manager
        self.dict_manager = SemanticDictionaryManager()
        
        # Initialize semantic filter compiler
        self.filter_compiler = SemanticFilterCompiler()
        self.semantic_filter = None
        
        # Results storage
        self.matches: List[MatchResult] = []
        self.evidence: List[ViolationEvidence] = []
        self.report: Optional[Dict] = None
        self.detected_language = 'en'
        self.semantic_dict = None
        self.term_embeddings = {}
        self.filter_hash = ''
    
    def _to_vector_str(self, embedding_list: List[float]) -> str:
        return '[' + ','.join(str(x) for x in embedding_list) + ']'
    
    async def get_codes_by_jurisdiction(self, jurisdiction: str) -> List[Dict]:
        """Get all codes for a jurisdiction."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            rows = await conn.fetch("""
                SELECT 
                    id, code_id, jurisdiction, section_number, title, content, severity, category, embedding
                FROM cais.construction_codes
                WHERE jurisdiction ILIKE $1
                ORDER BY severity DESC, code_id
            """, f"%{jurisdiction}%")
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def detect_document_language(self, document_text: str) -> str:
        """Detect the language of the document."""
        if not document_text or len(document_text.strip()) < 50:
            return 'en'
        
        try:
            sample = document_text[:1000]
            lang = detect(sample)
            if lang in self.dict_manager.SUPPORTED_LANGUAGES:
                return lang
            return 'en'
        except:
            return 'en'
    
    async def compile_semantic_filter(self, jurisdiction: str):
        """Compile semantic filter from codes."""
        print("\n📋 Compiling semantic filter for jurisdiction...")
        self.semantic_filter = await self.filter_compiler.compile_filter(jurisdiction)
        self.term_embeddings = self.filter_compiler.term_embeddings
        self.filter_hash = self.filter_compiler.filter_hash
        
        if self.semantic_filter:
            print(f"   ✅ Filter compiled: {self.semantic_filter.get('total_terms', 0)} terms")
            print(f"   ✅ Filter hash: {self.filter_hash[:16]}...")
    
    async def match_document(
        self, 
        document_text: str, 
        jurisdiction: str,
        pdf_path: Optional[str] = None,
        document_name: str = 'Unknown',
        use_filter: bool = True
    ) -> Tuple[List[MatchResult], List[ViolationEvidence]]:
        """
        Match a document against all codes using intelligent semantic comparison.
        
        Args:
            document_text: The document text to match
            jurisdiction: Jurisdiction for codes
            pdf_path: Optional PDF path for evidence generation
            document_name: Name of the document
            use_filter: Whether to use semantic filter for initial matching
        
        Returns:
            Tuple of (matches, evidence)
        """
        print("\n" + "="*70)
        print(" CODEMATCHER ADVANCED - INTELLIGENT MATCHING")
        print("="*70)
        print(f"   Document: {document_name}")
        print(f"   Jurisdiction: {jurisdiction}")
        print(f"   Text length: {len(document_text)} characters")
        print(f"   Using semantic filter: {use_filter}")
        
        # 1. Detect language
        self.detected_language = await self.detect_document_language(document_text)
        print(f"\n🌍 Detected language: {self.detected_language}")
        
        # 2. Load semantic dictionary for the language
        self.semantic_dict = self.dict_manager.get_dictionary(self.detected_language)
        print(f"   📚 Dictionary loaded: {self.semantic_dict.language_name}")
        print(f"      Terms: {len(self.semantic_dict.terms)}")
        print(f"      Categories: {len(self.semantic_dict.categories)}")
        
        # 3. Compile semantic filter
        if use_filter:
            await self.compile_semantic_filter(jurisdiction)
        
        # 4. Get codes for jurisdiction
        codes = await self.get_codes_by_jurisdiction(jurisdiction)
        if not codes:
            print("   ❌ No codes found for jurisdiction")
            return [], []
        
        print(f"   📋 {len(codes)} codes loaded")
        
        # 5. Extract sections from document
        sections = self._extract_sections(document_text)
        print(f"   📝 {len(sections)} sections extracted")
        
        # 6. Extract terms from sections
        all_document_terms = self._extract_all_terms(document_text)
        print(f"   🔤 {len(all_document_terms)} unique terms found in document")
        
        # 7. Match sections against codes
        all_matches = []
        processed = 0
        
        for idx, section in enumerate(sections):
            processed += 1
            if processed % 10 == 0:
                print(f"      Processing: {processed}/{len(sections)}")
            
            # Use semantic filter for initial filtering
            if use_filter and self.semantic_filter:
                # Find matching terms in the filter
                matching_terms = self._find_matching_terms(section, all_document_terms)
                if not matching_terms:
                    continue
            
            # Intelligent matching against codes
            matches = await self._intelligent_match(section, codes)
            all_matches.extend(matches)
        
        # 8. Deduplicate and rank matches
        self.matches = self._deduplicate_matches(all_matches)
        
        # 9. Generate visual evidence
        if pdf_path and self.matches:
            self.evidence = await self._generate_evidence(self.matches, pdf_path)
        
        # 10. Generate report
        self.report = self._generate_report()
        
        # 11. Print summary
        print(f"\n   ✅ Matching complete!")
        print(f"      Total matches: {len(self.matches)}")
        print(f"      Evidence generated: {len(self.evidence)}")
        
        return self.matches, self.evidence
    
    def _extract_sections(self, text: str) -> List[str]:
        """Extract sections from text."""
        # Split by paragraphs
        sections = text.split('\n\n')
        return [s.strip() for s in sections if len(s.strip()) > 50]
    
    def _extract_all_terms(self, text: str) -> Set[str]:
        """Extract all unique terms from text."""
        terms = set()
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        terms.update(words)
        
        # Extract phrases
        for phrase in self.filter_compiler.COMMON_PHRASES:
            if phrase in text.lower():
                terms.add(phrase)
        
        return terms
    
    def _find_matching_terms(self, section: str, document_terms: Set[str]) -> List[str]:
        """Find terms in the section that match the semantic filter."""
        section_lower = section.lower()
        matching_terms = []
        
        for term in self.semantic_filter.get('terms', []):
            if term in section_lower:
                matching_terms.append(term)
        
        for phrase in self.semantic_filter.get('phrases', []):
            if phrase in section_lower:
                matching_terms.append(phrase)
        
        return matching_terms
    
    async def _intelligent_match(self, section: str, codes: List[Dict]) -> List[MatchResult]:
        """
        Intelligent matching using multiple strategies.
        """
        matches = []
        section_lower = section.lower()
        section_words = set(section_lower.split())
        
        for code in codes:
            code_content = code.get('content', '')
            code_id = code.get('code_id', '')
            
            if not code_content:
                continue
            
            code_lower = code_content.lower()
            code_words = set(code_lower.split())
            
            # Strategy 1: Semantic similarity
            semantic_score = await self._calculate_semantic_score(section, code_content)
            
            # Strategy 2: Term overlap score
            term_overlap = len(section_words & code_words) / max(len(section_words), len(code_words))
            
            # Strategy 3: Keyword matching with dictionary
            keyword_score = self._calculate_keyword_score(section_lower, code_lower, code_id)
            
            # Strategy 4: Pattern matching
            pattern_score = self._calculate_pattern_score(section_lower, code_lower)
            
            # Combined score (weighted)
            combined_score = (
                semantic_score * 0.4 +
                term_overlap * 0.3 +
                keyword_score * 0.2 +
                pattern_score * 0.1
            )
            
            # Boost score if terms match the filter
            if self.semantic_filter:
                filter_boost = self._calculate_filter_boost(section_lower, code_lower)
                combined_score = min(combined_score + filter_boost * 0.1, 1.0)
            
            if combined_score >= 0.55:
                matched_terms = self._extract_matched_terms(section_lower, code_lower)
                term_details = self._get_term_match_details(section_lower, code_lower)
                
                match = MatchResult(
                    code_id=code_id,
                    code_content=code_content[:500],
                    jurisdiction=code.get('jurisdiction', 'Unknown'),
                    severity=self._determine_severity(combined_score),
                    similarity_score=combined_score,
                    matched_text=section[:200],
                    context=self._get_context(section, code_content, 100),
                    confidence=combined_score,
                    match_type=self._determine_match_type(semantic_score, keyword_score, pattern_score),
                    page_number=1,
                    matched_terms=matched_terms[:10],
                    term_match_details=term_details[:10]
                )
                matches.append(match)
        
        return matches
    
    async def _calculate_semantic_score(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using embeddings."""
        try:
            emb1 = self.model.encode(text1[:512])
            emb2 = self.model.encode(text2[:512])
            cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(cosine_sim)
        except:
            return 0.0
    
    def _calculate_keyword_score(self, text: str, code_content: str, code_id: str) -> float:
        """Calculate keyword matching score using semantic dictionary."""
        # Extract keywords from text
        keywords = self._extract_keywords(text)
        
        if not keywords:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            if keyword in code_content or keyword in code_id.lower():
                matches += 1
        
        total = len(keywords)
        score = matches / total if total > 0 else 0
        return min(score, 0.9)
    
    def _calculate_pattern_score(self, text: str, code_content: str) -> float:
        """Calculate pattern matching score."""
        patterns = {
            r'\b\d{1,3}\s*(?:in|"|inch)\b': 'dimension',
            r'\b\d{1,3}\s*(?:ft|feet)\b': 'dimension',
            r'\b(?:minimum|maximum)\b': 'requirement',
            r'\b(?:shall|must|required)\b': 'mandatory',
            r'\b(?:should|recommended|advisable)\b': 'advisory'
        }
        
        matched = 0
        total = 0
        
        for pattern, category in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                total += 1
                if category in code_content:
                    matched += 1
        
        if total == 0:
            return 0.0
        
        return matched / total
    
    def _calculate_filter_boost(self, section: str, code_content: str) -> float:
        """Calculate boost score based on semantic filter matching."""
        if not self.semantic_filter:
            return 0.0
        
        filter_terms = set(self.semantic_filter.get('terms', [])[:100])
        section_terms = set(re.findall(r'\b[a-zA-Z]{3,}\b', section))
        code_terms = set(re.findall(r'\b[a-zA-Z]{3,}\b', code_content))
        
        common_section = len(section_terms & filter_terms)
        common_code = len(code_terms & filter_terms)
        
        if common_section > 0 and common_code > 0:
            return min(common_section / 10, common_code / 10, 1.0)
        
        return 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using semantic dictionary."""
        keywords = []
        
        for term, translations in self.semantic_dict.terms.items():
            for word in translations:
                if word in text:
                    keywords.append(term)
                    break
        
        for tech_term in self.semantic_dict.technical_terms:
            if tech_term in text and tech_term not in keywords:
                keywords.append(tech_term)
        
        return list(set(keywords))
    
    def _extract_matched_terms(self, text: str, code_content: str) -> List[str]:
        """Extract terms that matched between text and code."""
        matched = []
        
        for term, translations in self.semantic_dict.terms.items():
            for word in translations:
                if word in text and word in code_content:
                    matched.append(word)
                    break
        
        return matched[:10]
    
    def _get_term_match_details(self, section: str, code_content: str) -> List[Dict]:
        """Get detailed term matching information."""
        details = []
        section_words = set(section.split())
        code_words = set(code_content.split())
        
        common = section_words & code_words
        for word in list(common)[:10]:
            details.append({
                'term': word,
                'in_section': True,
                'in_code': True,
                'score': 0.9
            })
        
        return details
    
    def _determine_severity(self, score: float) -> str:
        """Determine severity based on similarity score."""
        for severity, threshold in self.THRESHOLDS.items():
            if score >= threshold:
                return severity
        return 'low'
    
    def _determine_match_type(self, semantic: float, keyword: float, pattern: float) -> str:
        """Determine the match type."""
        if semantic >= 0.75:
            return 'semantic'
        elif keyword >= 0.65:
            return 'keyword'
        elif pattern >= 0.6:
            return 'pattern'
        else:
            return 'hybrid'
    
    def _get_context(self, text: str, code_content: str, chars: int = 100) -> str:
        """Get context around a match."""
        text_words = set(text.lower().split())
        code_words = set(code_content.lower().split())
        common = text_words & code_words
        
        if common:
            for word in common[:3]:
                index = text.lower().find(word)
                if index != -1:
                    start = max(0, index - chars//2)
                    end = min(len(text), index + len(word) + chars//2)
                    return text[start:end]
        
        return text[:chars]
    
    def _deduplicate_matches(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Deduplicate matches, keeping the best ones."""
        unique = {}
        
        for match in matches:
            key = f"{match.code_id}_{match.matched_text[:50]}"
            if key not in unique or unique[key].similarity_score < match.similarity_score:
                unique[key] = match
        
        return sorted(unique.values(), key=lambda x: x.similarity_score, reverse=True)
    
    async def _generate_evidence(self, matches: List[MatchResult], pdf_path: str) -> List[ViolationEvidence]:
        """Generate visual evidence for matches."""
        evidence_list = []
        
        if not matches or not Path(pdf_path).exists():
            return evidence_list
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence_dir = self.evidence_dir / f"evidence_{timestamp}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF pages to images
        try:
            images = convert_from_path(pdf_path, dpi=200)
        except:
            images = []
        
        for idx, match in enumerate(matches[:20]):
            page_num = min(match.page_number, len(images)) if images else 1
            page_image = images[page_num - 1] if images else None
            
            # Generate RED box evidence
            screenshot_path = self._generate_red_box_evidence(
                page_image, page_num, match, evidence_dir, idx
            )
            
            # Generate YELLOW highlight evidence
            highlight_path = self._generate_yellow_highlight_evidence(
                match, evidence_dir, idx
            )
            
            evidence = ViolationEvidence(
                violation_id=f"EVI-{timestamp}-{idx+1:04d}",
                code_id=match.code_id,
                severity=match.severity,
                similarity_score=match.similarity_score,
                document_text=match.matched_text,
                code_text=match.code_content,
                page_number=page_num,
                screenshot_path=str(screenshot_path) if screenshot_path else "",
                code_highlight_path=str(highlight_path),
                matched_terms=match.matched_terms,
                language=self.detected_language,
                confidence=match.confidence,
                term_match_details=match.term_match_details
            )
            evidence_list.append(evidence)
        
        return evidence_list
    
    def _generate_red_box_evidence(self, image, page_num: int, match: MatchResult, evidence_dir: Path, idx: int):
        """Generate RED box evidence on the document image."""
        if image is None:
            filepath = evidence_dir / f"redbox_violation_{idx+1:04d}.txt"
            content = f"""
============================================================
VIOLATION EVIDENCE - RED BOX (Text-based)
============================================================
Violation ID: EVI-{datetime.now().strftime('%Y%m%d_%H%M%S')}-{idx+1:04d}
Code: {match.code_id}
Severity: {match.severity.upper()}
Similarity: {match.similarity_score:.3f}
Page: {page_num}

VIOLATION TEXT:
{match.matched_text}

CODE VIOLATED:
{match.code_content[:500]}

MATCHED TERMS:
{', '.join(match.matched_terms[:5])}
============================================================
"""
            with open(filepath, 'w') as f:
                f.write(content)
            return filepath
        
        try:
            img = image.copy()
            draw = ImageDraw.Draw(img)
            
            # Search for text in image using OCR
            import pytesseract
            try:
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                text = match.matched_text[:100]
                
                x, y, w, h = 100, 100, 200, 50
                for i, word in enumerate(data['text']):
                    if len(word) > 3 and word.lower() in text.lower():
                        x = data['left'][i]
                        y = data['top'][i]
                        w = data['width'][i]
                        h = data['height'][i]
                        break
            except:
                x, y, w, h = 100, 100, 200, 50
            
            padding = 30
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = w + padding * 2
            h = h + padding * 2
            
            severity_colors = {
                'critical': (204, 0, 0),
                'high': (204, 102, 0),
                'medium': (204, 136, 0),
                'low': (0, 102, 204)
            }
            color = severity_colors.get(match.severity, (204, 0, 0))
            
            draw.rectangle([(x, y), (x + w, y + h)], outline=color, width=5)
            
            label_y = y - 30 if y > 30 else y + 10
            draw.rectangle(
                [(x, label_y), (x + 200, label_y + 28)],
                fill=(*color, 220)
            )
            
            try:
                font = ImageFont.truetype("Arial", 14)
            except:
                font = ImageFont.load_default()
            
            draw.text(
                (x + 5, label_y + 5),
                f"{match.severity.upper()} VIOLATION",
                fill=(255, 255, 255),
                font=font
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
            filepath = evidence_dir / f"redbox_violation_{idx+1:04d}_{timestamp}.png"
            img.save(filepath, 'PNG')
            
            return filepath
            
        except Exception as e:
            print(f"   ⚠️ Error generating red box: {e}")
            filepath = evidence_dir / f"redbox_violation_{idx+1:04d}.txt"
            with open(filepath, 'w') as f:
                f.write(f"Violation: {match.code_id}\nSeverity: {match.severity}\nText: {match.matched_text}")
            return filepath
    
    def _generate_yellow_highlight_evidence(self, match: MatchResult, evidence_dir: Path, idx: int) -> Path:
        """Generate YELLOW highlight evidence for the code section."""
        filepath = evidence_dir / f"yellow_highlight_{idx+1:04d}.txt"
        
        content = f"""
============================================================
CODE VIOLATION EVIDENCE - YELLOW HIGHLIGHT
============================================================
Code ID: {match.code_id}
Jurisdiction: {match.jurisdiction}
Severity: {match.severity.upper()}
Similarity Score: {match.similarity_score:.3f}
Match Type: {match.match_type}
Matched Terms: {', '.join(match.matched_terms[:5])}

HIGHLIGHTED CODE SECTION (Violated):
------------------------------------------------------------
>>> {match.code_content[:500]} <<<
------------------------------------------------------------

DOCUMENT CONTEXT:
{match.context}

TERM MATCH DETAILS:
{json.dumps(match.term_match_details[:5], indent=2)}

Confidence: {match.confidence:.3f}
Generated: {datetime.now().isoformat()}
============================================================
"""
        with open(filepath, 'w') as f:
            f.write(content)
        
        return filepath
    
    def _generate_report(self) -> Dict:
        """Generate a complete report of all matches and evidence."""
        severity_counts = defaultdict(int)
        match_types = defaultdict(int)
        
        for match in self.matches:
            severity_counts[match.severity] += 1
            match_types[match.match_type] += 1
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'detected_language': self.detected_language,
            'filter_hash': self.filter_hash,
            'total_matches': len(self.matches),
            'total_evidence': len(self.evidence),
            'severity_breakdown': dict(severity_counts),
            'match_type_breakdown': dict(match_types),
            'matches': [
                {
                    'code_id': m.code_id,
                    'severity': m.severity,
                    'similarity': m.similarity_score,
                    'match_type': m.match_type,
                    'matched_terms': m.matched_terms[:5],
                    'confidence': m.confidence
                }
                for m in self.matches[:50]
            ],
            'evidence': [
                {
                    'violation_id': e.violation_id,
                    'code_id': e.code_id,
                    'severity': e.severity,
                    'page': e.page_number,
                    'screenshot': e.screenshot_path
                }
                for e in self.evidence[:20]
            ]
        }
        
        # Save report
        report_dir = Path('./reports')
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f'code_matcher_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📋 Report saved: {report_path}")
        
        return report


async def main():
    """Test the CodeMatcher Advanced."""
    import glob
    
    print("\n" + "="*70)
    print(" CODEMATCHER ADVANCED - TEST RUN")
    print(" Intelligent Semantic Matching with Visual Evidence")
    print("="*70)
    
    # Find PDF
    pdf_files = glob.glob('/home/maxlo/PROMETHEUS/blueprints/*.pdf')
    if not pdf_files:
        pdf_files = glob.glob('/home/maxlo/PROMETHEUS/downloads/*/INTL_*.pdf')
    if not pdf_files:
        print("❌ No PDFs found")
        return
    
    pdf_path = pdf_files[0]
    
    # Extract text from PDF
    from src.agents.plan_inspector_agent import PlanInspectorAgent
    inspector = PlanInspectorAgent()
    sections, full_text = inspector.extract_sections_from_document(str(pdf_path))
    
    print(f"\n📄 PDF: {Path(pdf_path).name}")
    print(f"   Sections: {len(sections)}")
    print(f"   Total text: {len(full_text)} characters")
    
    # Initialize CodeMatcher
    matcher = CodeMatcherAdvanced(evidence_dir="./evidence")
    
    # Run matching
    matches, evidence = await matcher.match_document(
        document_text=full_text,
        jurisdiction='Florida',
        pdf_path=str(pdf_path),
        document_name=Path(pdf_path).name,
        use_filter=True
    )
    
    print("\n" + "="*70)
    print(" CODEMATCHER ADVANCED - COMPLETE")
    print("="*70)
    print(f"   Total matches: {len(matches)}")
    print(f"   Evidence generated: {len(evidence)}")
    
    if matches:
        print(f"\n📊 SEVERITY BREAKDOWN:")
        for severity in ['critical', 'high', 'medium', 'low']:
            count = sum(1 for m in matches if m.severity == severity)
            if count > 0:
                print(f"   {severity.upper()}: {count}")
        
        print(f"\n📊 MATCH TYPE BREAKDOWN:")
        for match_type in ['semantic', 'keyword', 'pattern', 'hybrid']:
            count = sum(1 for m in matches if m.match_type == match_type)
            if count > 0:
                print(f"   {match_type.upper()}: {count}")
    
    print(f"\n🔑 Filter Hash: {matcher.filter_hash[:16]}...")


if __name__ == "__main__":
    asyncio.run(main())
