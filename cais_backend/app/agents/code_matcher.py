#!/usr/bin/env python3
"""
CodeMatcher - Semantic search using pgvector with top‑k results.
"""

import os
import logging
from typing import Dict, List, Optional
import asyncpg
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CodeMatcher:
    def __init__(self, model_name='all-MiniLM-L6-v2', top_k=3, min_sim=0.55):
        self.model = SentenceTransformer(model_name)
        self.top_k = top_k
        self.min_sim = min_sim
        self.db_config = {
            "host": os.getenv("CAIS_PG_HOST", "postgres"),
            "port": int(os.getenv("CAIS_PG_PORT", "5432")),
            "user": os.getenv("CAIS_PG_USER", "cais"),
            "password": os.getenv("CAIS_PG_PASSWORD", "cais123"),
            "database": os.getenv("CAIS_PG_DATABASE", "cais_db")
        }
        self._conn = None

    async def connect_db(self):
        if self._conn is None:
            self._conn = await asyncpg.connect(**self.db_config)
        return self._conn

    async def close_db(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def match_top_k(self, text: str, jurisdiction: Optional[str] = None, top_k: Optional[int] = None) -> List[Dict]:
        if not text or len(text.strip()) < 10:
            return []
        top_k = top_k or self.top_k
        embedding = self.model.encode(text, normalize_embeddings=True).tolist()
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        conn = await self.connect_db()
        query = """
            SELECT code_id, jurisdiction, section_number, title, content, category,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM code_sections
            WHERE embedding IS NOT NULL
        """
        params = [embedding_str]
        if jurisdiction:
            query += " AND jurisdiction = $2"
            params.append(jurisdiction)
        query += " ORDER BY similarity DESC LIMIT $3"
        params.append(top_k)
        rows = await conn.fetch(query, *params)
        results = []
        for row in rows:
            if row['similarity'] >= self.min_sim:
                results.append({
                    "code": row['code_id'],
                    "jurisdiction": row['jurisdiction'],
                    "section_number": row['section_number'],
                    "title": row['title'],
                    "content": row['content'],
                    "category": row['category'],
                    "confidence": round(row['similarity'], 3)
                })
        return results

    async def match_single(self, text: str, jurisdiction: Optional[str] = None) -> Optional[Dict]:
        matches = await self.match_top_k(text, jurisdiction, top_k=1)
        return matches[0] if matches else None
