#!/usr/bin/env python3
"""
Semantic Indexer - CAIS Autopoietic System
Índice semántico para búsqueda de códigos normativos
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Resultado de búsqueda semántica"""
    section_id: str
    code_id: str
    section_number: str
    title: str
    content: str
    score: float
    keywords: List[str]
    jurisdiction: str

class SemanticIndexer:
    """
    Índice semántico para búsqueda de códigos normativos.
    Utiliza Sentence-BERT para embeddings y FAISS para búsqueda eficiente.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.sections: List[Dict] = []
        self.dimension = 384  # all-MiniLM-L6-v2
        self.is_built = False
        
        logger.info(f"SemanticIndexer initialized with model: {model_name}")
    
    def build_index(self, sections: List[Dict]) -> None:
        """
        Construye el índice a partir de secciones de código.
        
        Args:
            sections: Lista de secciones con contenido y metadatos
        """
        logger.info(f"Building index with {len(sections)} sections...")
        
        self.sections = sections
        
        # Extraer textos para embeddings
        texts = []
        for section in sections:
            # Combinar título y contenido para mejor embedding
            text = f"{section.get('title', '')} {section.get('content', '')[:500]}"
            texts.append(text)
        
        # Generar embeddings
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        
        # Crear índice FAISS
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.is_built = True
        
        logger.info(f"✅ Index built with {len(sections)} sections")
    
    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Busca secciones por similitud semántica.
        
        Args:
            query: Texto de búsqueda
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de SearchResult ordenados por relevancia
        """
        if not self.is_built:
            logger.warning("Index not built yet")
            return []
        
        # Generar embedding de la consulta
        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).reshape(1, -1)
        
        # Buscar en el índice
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.sections):
                section = self.sections[idx]
                results.append(SearchResult(
                    section_id=section.get('section_number', ''),
                    code_id=section.get('code_id', ''),
                    section_number=section.get('section_number', ''),
                    title=section.get('title', ''),
                    content=section.get('content', '')[:300] + '...',
                    score=float(score),
                    keywords=section.get('keywords', []),
                    jurisdiction=section.get('jurisdiction', 'IBC')
                ))
        
        return results
    
    def search_by_jurisdiction(self, query: str, jurisdiction: str, top_k: int = 10) -> List[SearchResult]:
        """Busca filtrando por jurisdicción"""
        results = self.search(query, top_k=top_k * 2)
        
        # Filtrar por jurisdicción
        filtered = [r for r in results if r.jurisdiction.lower() == jurisdiction.lower()]
        return filtered[:top_k]
    
    def get_similar_sections(self, section_id: str, top_k: int = 5) -> List[SearchResult]:
        """Encuentra secciones similares a una dada"""
        # Encontrar la sección por ID
        section = None
        for s in self.sections:
            if s.get('section_number') == section_id:
                section = s
                break
        
        if not section:
            return []
        
        # Usar título como consulta
        query = f"{section.get('title', '')} {section.get('content', '')[:300]}"
        results = self.search(query, top_k=top_k + 1)
        
        # Excluir la sección original
        return [r for r in results if r.section_number != section_id][:top_k]
    
    def save_index(self, output_dir: Path) -> None:
        """Guarda el índice y las secciones en disco"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar secciones
        sections_path = output_dir / "sections.json"
        sections_path.write_text(json.dumps(self.sections, indent=2, default=str))
        
        # Guardar índice FAISS
        if self.index:
            index_path = output_dir / "faiss.index"
            faiss.write_index(self.index, str(index_path))
        
        logger.info(f"✅ Index saved to {output_dir}")
    
    def load_index(self, input_dir: Path) -> None:
        """Carga el índice desde disco"""
        input_dir = Path(input_dir)
        
        # Cargar secciones
        sections_path = input_dir / "sections.json"
        if sections_path.exists():
            self.sections = json.loads(sections_path.read_text())
        
        # Cargar índice FAISS
        index_path = input_dir / "faiss.index"
        if index_path.exists():
            self.index = faiss.read_index(str(index_path))
            self.is_built = True
        
        logger.info(f"✅ Index loaded from {input_dir} ({len(self.sections)} sections)")


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🔍 SEMANTIC INDEXER - CAIS AUTOPOIETIC SYSTEM        ║
║                                                           ║
║     Construyendo índice semántico...                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Cargar secciones desde el output del LawsIngestor
    laws_output = Path("~/PROMETHEUS/output/laws").expanduser()
    sections_path = laws_output / "all_sections.json"
    
    if sections_path.exists():
        sections = json.loads(sections_path.read_text())
        
        # Construir índice
        indexer = SemanticIndexer()
        indexer.build_index(sections)
        
        # Guardar índice
        index_output = Path("~/PROMETHEUS/output/semantic_index").expanduser()
        indexer.save_index(index_output)
        
        # Probar búsqueda
        test_queries = [
            "fire safety requirements",
            "structural load calculations",
            "accessibility for disabled",
            "energy efficiency standards",
            "building occupancy limits"
        ]
        
        print("\n" + "="*60)
        print("🔍 TEST SEARCH RESULTS")
        print("="*60)
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            results = indexer.search(query, top_k=3)
            for i, r in enumerate(results, 1):
                print(f"   {i}. [{r.code_id}] {r.section_number} - {r.title[:50]}...")
                print(f"      Score: {r.score:.3f} | Jurisdiction: {r.jurisdiction}")
        
        print("\n" + "="*60)
        print(f"📁 Index saved to: {index_output}")
    else:
        print("❌ No sections found. Run LawsIngestor first.")
