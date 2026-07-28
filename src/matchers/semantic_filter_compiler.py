#!/usr/bin/env python3
"""
Semantic Filter Compiler - CAIS
Compiles a semantic filter from construction codes, regulations, and laws.
Extracts all terms, keywords, and phrases for semantic search.
100% ENGLISH - All comments, messages, and logs in English.
"""

import os
import sys
import json
import re
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import hashlib

from sentence_transformers import SentenceTransformer
import numpy as np


class SemanticFilterCompiler:
    """
    Compiles a semantic filter from construction codes, regulations, and laws.
    Extracts ALL terms, keywords, and phrases for semantic matching.
    """
    
    # Technical term patterns
    TERM_PATTERNS = {
        'dimensions': [
            r'\b\d{1,3}\s*(?:in|"|inch|ft|feet|mm|cm|m)\b',
            r'\b(?:width|height|depth|length|clearance|opening|span)\b'
        ],
        'requirements': [
            r'\b(?:minimum|maximum|required|shall|must|should|recommended)\b',
            r'\b(?:not less than|not exceed|no more than|at least)\b'
        ],
        'materials': [
            r'\b(?:steel|concrete|wood|masonry|aluminum|glass|plastic|composite)\b',
            r'\b(?:grade|type|class|standard|specification)\b'
        ],
        'systems': [
            r'\b(?:structural|electrical|plumbing|mechanical|hvac|fire|safety)\b',
            r'\b(?:beam|column|foundation|wall|floor|roof|ceiling)\b'
        ],
        'actions': [
            r'\b(?:install|provide|construct|design|build|maintain|inspect|test)\b',
            r'\b(?:verify|check|confirm|ensure|validate)\b'
        ]
    }
    
    # Common construction phrases
    COMMON_PHRASES = [
        'means of egress', 'fire protection', 'structural integrity',
        'load bearing', 'safety factor', 'building code', 'compliance',
        'construction document', 'design criteria', 'installation method',
        'quality control', 'inspection requirement', 'test procedure',
        'maintenance schedule', 'repair method', 'replacement procedure'
    ]
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"✅ Model loaded: {self.model.get_sentence_embedding_dimension()} dimensions")
        
        self.terms: Set[str] = set()
        self.phrases: Set[str] = set()
        self.keywords: Dict[str, List[str]] = defaultdict(list)
        self.term_embeddings: Dict[str, List[float]] = {}
        self.filter_hash: str = ''
    
    async def compile_filter(self, jurisdiction: str = None) -> Dict:
        """
        Compile the semantic filter from all codes.
        
        Args:
            jurisdiction: Optional jurisdiction filter
        
        Returns:
            Compiled filter data
        """
        print("\n" + "="*70)
        print(" SEMANTIC FILTER COMPILER")
        print(" Extracting terms from construction codes")
        print("="*70)
        
        # Get all codes
        codes = await self._get_codes(jurisdiction)
        
        if not codes:
            print("❌ No codes found")
            return {}
        
        print(f"📋 {len(codes)} codes found")
        
        # Extract terms from codes
        print("\n🔍 Extracting terms from codes...")
        
        for idx, code in enumerate(codes):
            if (idx + 1) % 50 == 0:
                print(f"   Processing: {idx+1}/{len(codes)}")
            
            content = code.get('content', '')
            title = code.get('title', '')
            code_id = code.get('code_id', '')
            category = code.get('category', '')
            severity = code.get('severity', '')
            
            # Extract terms from content
            self._extract_terms_from_text(content)
            self._extract_terms_from_text(title)
            self._extract_terms_from_text(code_id)
            
            # Add category and severity as keywords
            if category:
                self.keywords['category'].append(category)
            if severity:
                self.keywords['severity'].append(severity)
        
        print(f"\n   ✅ Extracted {len(self.terms)} unique terms")
        print(f"   ✅ Extracted {len(self.phrases)} unique phrases")
        print(f"   ✅ Extracted {len(self.keywords)} keyword categories")
        
        # Generate embeddings for all terms
        print("\n🧠 Generating embeddings for terms...")
        self._generate_embeddings()
        
        # Calculate filter hash
        self._calculate_hash()
        
        # Compile final filter
        filter_data = {
            'timestamp': datetime.now().isoformat(),
            'jurisdiction': jurisdiction or 'all',
            'total_terms': len(self.terms),
            'total_phrases': len(self.phrases),
            'terms': list(self.terms),
            'phrases': list(self.phrases),
            'keywords': dict(self.keywords),
            'hash': self.filter_hash,
            'embedding_dimension': self.model.get_sentence_embedding_dimension()
        }
        
        # Save filter
        self._save_filter(filter_data)
        
        print("\n" + "="*70)
        print(" FILTER COMPILATION COMPLETE")
        print("="*70)
        print(f"   Total terms: {len(self.terms)}")
        print(f"   Total phrases: {len(self.phrases)}")
        print(f"   Embedding dimension: {filter_data['embedding_dimension']}")
        print(f"   Hash: {self.filter_hash[:16]}...")
        
        return filter_data
    
    async def _get_codes(self, jurisdiction: str = None) -> List[Dict]:
        """Get codes from database."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            if jurisdiction:
                rows = await conn.fetch("""
                    SELECT code_id, jurisdiction, section_number, title, content, severity, category
                    FROM cais.construction_codes
                    WHERE jurisdiction ILIKE $1
                """, f"%{jurisdiction}%")
            else:
                rows = await conn.fetch("""
                    SELECT code_id, jurisdiction, section_number, title, content, severity, category
                    FROM cais.construction_codes
                """)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    def _extract_terms_from_text(self, text: str):
        """Extract terms and phrases from text."""
        if not text:
            return
        
        text_lower = text.lower()
        
        # Extract terms from patterns
        for pattern_type, patterns in self.TERM_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        for part in match:
                            if len(part) > 1:
                                self.terms.add(part.strip())
                    else:
                        if len(match) > 1:
                            self.terms.add(match.strip())
                    self.keywords[pattern_type].append(match if isinstance(match, str) else str(match))
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text_lower)
        for word in words:
            if len(word) > 2:
                self.terms.add(word)
        
        # Extract phrases (3-4 word combinations)
        sentences = re.split(r'[.!?]+', text_lower)
        for sentence in sentences:
            words = sentence.split()
            for i in range(len(words) - 1):
                # 2-word phrases
                self.phrases.add(' '.join(words[i:i+2]))
                if i < len(words) - 2:
                    # 3-word phrases
                    self.phrases.add(' '.join(words[i:i+3]))
        
        # Add common phrases
        for phrase in self.COMMON_PHRASES:
            if phrase in text_lower:
                self.phrases.add(phrase)
    
    def _generate_embeddings(self):
        """Generate embeddings for all terms."""
        all_terms = list(self.terms) + list(self.phrases)
        
        if not all_terms:
            return
        
        # Generate embeddings in batches
        batch_size = 100
        for i in range(0, len(all_terms), batch_size):
            batch = all_terms[i:i+batch_size]
            embeddings = self.model.encode(batch)
            
            for j, term in enumerate(batch):
                self.term_embeddings[term] = embeddings[j].tolist()
        
        print(f"   ✅ Generated embeddings for {len(self.term_embeddings)} terms")
    
    def _calculate_hash(self):
        """Calculate hash of the filter."""
        content = json.dumps({
            'terms': sorted(self.terms),
            'phrases': sorted(self.phrases),
            'keywords': dict(self.keywords)
        }, sort_keys=True)
        self.filter_hash = hashlib.sha256(content.encode()).hexdigest()
    
    def _save_filter(self, filter_data: Dict):
        """Save filter to file."""
        output_dir = Path('./semantic_filters')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filter_path = output_dir / f'semantic_filter_{timestamp}.json'
        
        with open(filter_path, 'w') as f:
            json.dump(filter_data, f, indent=2)
        
        print(f"\n📁 Filter saved: {filter_path}")
        
        # Also save to database
        asyncio.create_task(self._save_filter_to_db(filter_data))
    
    async def _save_filter_to_db(self, filter_data: Dict):
        """Save filter to database."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            await conn.execute("""
                INSERT INTO cais.semantic_filters 
                (document_id, jurisdiction, terms, embeddings, term_frequencies, total_terms, unique_terms, hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                f"FILTER_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                filter_data.get('jurisdiction', 'all'),
                json.dumps({
                    'terms': filter_data['terms'],
                    'phrases': filter_data['phrases']
                }),
                json.dumps({k: v[:10] for k, v in self.term_embeddings.items()}),  # Limit embeddings
                json.dumps(filter_data['keywords']),
                filter_data['total_terms'],
                filter_data['total_phrases'],
                filter_data['hash']
            )
        except Exception as e:
            print(f"⚠️ Could not save filter to DB: {e}")
        finally:
            await conn.close()
    
    def search_with_filter(self, query: str, filter_data: Dict, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Search using the compiled filter.
        """
        if not self.term_embeddings:
            self._generate_embeddings()
        
        query_embedding = self.model.encode(query)
        
        results = []
        for term, embedding in self.term_embeddings.items():
            similarity = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
            results.append((term, float(similarity)))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


async def main():
    """Test the Semantic Filter Compiler."""
    print("\n" + "="*70)
    print(" SEMANTIC FILTER COMPILER - TEST")
    print("="*70)
    
    compiler = SemanticFilterCompiler()
    
    # Compile filter for Florida
    filter_data = await compiler.compile_filter(jurisdiction='Florida')
    
    # Test search with filter
    print("\n🔍 TESTING FILTER SEARCH:")
    test_queries = [
        "minimum door width",
        "guard rail height",
        "stair tread depth",
        "electrical outlet spacing",
        "fire sprinkler requirements"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        results = compiler.search_with_filter(query, filter_data, top_k=5)
        
        print("   Top matches:")
        for term, score in results:
            print(f"      - {term} ({score:.3f})")


if __name__ == "__main__":
    asyncio.run(main())
