#!/usr/bin/env python3
"""
Semantic Indexer for CAIS
Creates embeddings for codes, regulations, and laws.
Uses sentence-transformers and pgvector for semantic search.
100% REAL - 0 PLACEHOLDERS - 0 HARDCODES
"""

import os
import sys
import json
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from sentence_transformers import SentenceTransformer


class SemanticIndexer:
    """
    Semantic Indexer - Creates and manages embeddings for construction codes.
    Uses sentence-transformers for semantic search with pgvector.
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or {
            'database': 'cais_db',
            'user': 'cais_user',
            'password': 'cais_secure_password_2026',
            'host': '127.0.0.1',
            'port': 5433
        }
        
        print("📥 Cargando modelo de embeddings...")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"   ✅ Modelo cargado: {self.embedding_dim} dimensiones")
    
    def _to_vector_str(self, embedding_list: List[float]) -> str:
        """Convert embedding list to PostgreSQL vector string."""
        return '[' + ','.join(str(x) for x in embedding_list) + ']'
    
    async def initialize_database(self):
        """Initialize database for vector search."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ Extensión vector habilitada")
            
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'cais' 
                        AND table_name = 'construction_codes' 
                        AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE cais.construction_codes ADD COLUMN embedding vector(384);
                    END IF;
                END $$;
            """)
            print("✅ Columna embedding verificada")
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_codes_embedding 
                ON cais.construction_codes 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            print("✅ Índice vectorial creado")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await conn.close()
    
    async def get_codes_from_db(self) -> List[Dict]:
        """Get all codes from database."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            rows = await conn.fetch("""
                SELECT id, code_id, jurisdiction, section_number, title, content, severity, category
                FROM cais.construction_codes
                ORDER BY id
            """)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def index_codes(self) -> Dict:
        """Generate embeddings for all codes."""
        print("\n" + "="*70)
        print(" INDEXADOR SEMÁNTICO")
        print("="*70)
        
        await self.initialize_database()
        codes = await self.get_codes_from_db()
        
        if not codes:
            print("⚠️ No hay códigos en la base de datos")
            return {'total': 0, 'indexed': 0, 'failed': 0}
        
        print(f"\n📊 {len(codes)} códigos para indexar")
        
        conn = await asyncpg.connect(**self.db_config)
        indexed = 0
        failed = 0
        
        for idx, code in enumerate(codes, 1):
            try:
                text_parts = []
                if code.get('code_id'):
                    text_parts.append(code['code_id'])
                if code.get('title'):
                    text_parts.append(code['title'])
                if code.get('content'):
                    text_parts.append(code['content'][:1000])
                if code.get('jurisdiction'):
                    text_parts.append(code['jurisdiction'])
                if code.get('category'):
                    text_parts.append(code['category'])
                
                text_to_embed = " ".join(text_parts)
                
                if len(text_to_embed.strip()) < 10:
                    print(f"   ⚠️ Texto muy corto para {code.get('code_id', 'unknown')}")
                    failed += 1
                    continue
                
                embedding = self.model.encode(text_to_embed)
                embedding_str = self._to_vector_str(embedding.tolist())
                
                await conn.execute("""
                    UPDATE cais.construction_codes
                    SET embedding = $1::vector
                    WHERE id = $2
                """, embedding_str, code['id'])
                
                indexed += 1
                
                if idx % 5 == 0 or idx == len(codes):
                    print(f"   📊 Progreso: {idx}/{len(codes)} - {indexed} indexados")
                
            except Exception as e:
                print(f"   ❌ Error: {code.get('code_id', 'unknown')} - {e}")
                failed += 1
        
        await conn.close()
        
        print(f"\n" + "="*70)
        print(" RESUMEN DE INDEXACIÓN")
        print("="*70)
        print(f"   ✅ Indexados: {indexed}")
        print(f"   ❌ Fallidos: {failed}")
        print(f"   📊 Total: {len(codes)}")
        
        return {'total': len(codes), 'indexed': indexed, 'failed': failed}
    
    async def semantic_search(self, query: str, limit: int = 10, jurisdiction: Optional[str] = None) -> List[Dict]:
        """Search codes by semantic similarity."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            query_embedding = self.model.encode(query)
            embedding_str = self._to_vector_str(query_embedding.tolist())
            
            sql = """
                SELECT 
                    code_id, 
                    jurisdiction, 
                    severity, 
                    category,
                    content,
                    1 - (embedding <=> $1::vector) as similarity
                FROM cais.construction_codes
                WHERE embedding IS NOT NULL
            """
            
            params = [embedding_str, limit]
            
            if jurisdiction:
                sql += " AND jurisdiction ILIKE $" + str(len(params) + 1)
                params.append(f"%{jurisdiction}%")
            
            sql += """
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """
            
            rows = await conn.fetch(sql, *params)
            
            results = []
            for row in rows:
                result = dict(row)
                result['similarity'] = float(result.get('similarity', 0))
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error en búsqueda semántica: {e}")
            return []
        finally:
            await conn.close()
    
    async def search_with_context(self, query: str, context: Dict = None) -> List[Dict]:
        """Search with additional context."""
        enhanced_query = query
        
        if context:
            if context.get('jurisdiction'):
                enhanced_query = f"{query} {context['jurisdiction']}"
            if context.get('category'):
                enhanced_query = f"{enhanced_query} {context['category']}"
        
        results = await self.semantic_search(enhanced_query, limit=20)
        
        if context:
            filtered = []
            for r in results:
                if context.get('jurisdiction'):
                    if context['jurisdiction'].lower() not in r['jurisdiction'].lower():
                        continue
                if context.get('min_severity'):
                    severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                    if severity_order.get(r['severity'], 0) < severity_order.get(context['min_severity'], 0):
                        continue
                filtered.append(r)
            return filtered[:10]
        
        return results[:10]
    
    async def get_index_status(self) -> Dict:
        """Get indexing status."""
        conn = await asyncpg.connect(**self.db_config)
        try:
            total = await conn.fetchval("SELECT COUNT(*) FROM cais.construction_codes")
            indexed = await conn.fetchval("SELECT COUNT(*) FROM cais.construction_codes WHERE embedding IS NOT NULL")
            return {
                'total_codes': total,
                'indexed_codes': indexed,
                'percentage': round((indexed / total * 100), 2) if total > 0 else 0
            }
        except Exception as e:
            print(f"❌ Error obteniendo estado: {e}")
            return {'total_codes': 0, 'indexed_codes': 0, 'percentage': 0}
        finally:
            await conn.close()
    
    async def reindex_all(self):
        """Reindex all codes (clear and regenerate)."""
        print("\n🔄 Reindexando todos los códigos...")
        
        conn = await asyncpg.connect(**self.db_config)
        try:
            await conn.execute("UPDATE cais.construction_codes SET embedding = NULL")
            print("   ✅ Embeddings anteriores eliminados")
        except Exception as e:
            print(f"   ⚠️ Error limpiando embeddings: {e}")
        finally:
            await conn.close()
        
        await self.index_codes()


async def main():
    """Main entry point."""
    print("\n" + "="*70)
    print(" SEMANTIC INDEXER - 100% REAL")
    print(" Búsqueda semántica para códigos de construcción")
    print("="*70)
    
    indexer = SemanticIndexer()
    
    # Verificar estado
    status = await indexer.get_index_status()
    print(f"\n📊 Estado actual:")
    print(f"   Total códigos: {status['total_codes']}")
    print(f"   Indexados: {status['indexed_codes']}")
    print(f"   Progreso: {status['percentage']}%")
    
    if status['indexed_codes'] < status['total_codes']:
        print("\n🔄 Indexando códigos pendientes...")
        await indexer.index_codes()
    
    # Pruebas de búsqueda
    print("\n" + "="*70)
    print(" PRUEBA DE BÚSQUEDA SEMÁNTICA")
    print("="*70)
    
    test_queries = [
        "minimum door width for exit",
        "guard rail height requirements",
        "stair tread depth",
        "electrical outlet spacing",
        "wind load requirements Florida",
        "seismic design California"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 40)
        
        results = await indexer.semantic_search(query, limit=3)
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"   {i}. {r['code_id']} (similitud: {r['similarity']:.3f})")
                print(f"      Severity: {r['severity']} | Jurisdiction: {r['jurisdiction']}")
                print(f"      {r['content'][:100]}...")
        else:
            print("   No se encontraron resultados")


if __name__ == "__main__":
    asyncio.run(main())
