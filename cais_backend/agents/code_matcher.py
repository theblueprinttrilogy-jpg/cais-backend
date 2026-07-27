# agents/code_matcher.py - Advanced Multilingual Code Matcher for CAIS v2.0
# Production-ready semantic matcher for construction codes, safety regulations, and building laws.
# Supports multilingual text via language detection and multilingual embeddings.
# Integrates with PostgreSQL + pgvector for cosine similarity search with threshold 0.65.
# Provides robust language fallback, connection pooling, Pydantic validation, and forensic logging.

import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np

import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PsycopgConnection
from psycopg2.pool import SimpleConnectionPool

from pydantic import BaseModel, Field, ValidationError, validator

# Language detection
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed(0)
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None

# Embedding model
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------
class CodeEntry(BaseModel):
    """A single building code entry with its vector."""
    section: str = Field(..., description="Code section identifier (e.g., IBC 1006.2.1)")
    full_text: str = Field(..., description="Full text description of the code")
    source: str = Field(..., description="Source document or standard")
    language: Optional[str] = Field(None, description="ISO 639-1 language code of the text")

    @validator('language', pre=True, always=True)
    def set_language(cls, v, values):
        if v is None:
            # Auto-detect from full_text if available
            text = values.get('full_text', '')
            if text and LANGDETECT_AVAILABLE:
                try:
                    return detect(text)
                except Exception:
                    pass
            return 'en'  # fallback
        return v

class CodeMatchResult(BaseModel):
    """Result of a semantic match."""
    section: str
    full_text: str
    source: str
    similarity_score: float
    is_match: bool  # True if above threshold

class CodeMatcherConfig(BaseModel):
    """Configuration for CodeMatcher."""
    db_host: str = Field(default_factory=lambda: os.environ.get("DB_HOST", "localhost"))
    db_port: int = Field(default_factory=lambda: int(os.environ.get("DB_PORT", 5432)))
    db_name: str = Field(default_factory=lambda: os.environ.get("DB_NAME", "cais_db"))
    db_user: str = Field(default_factory=lambda: os.environ.get("DB_USER", "cais_user"))
    db_password: str = Field(default_factory=lambda: os.environ.get("DB_PASSWORD", "cais_password"))
    similarity_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for a match"
    )
    embedding_model_name: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        description="SentenceTransformer model name for multilingual embeddings"
    )
    pool_min_conn: int = Field(default=1)
    pool_max_conn: int = Field(default=10)
    vector_dimension: Optional[int] = Field(
        default=None,
        description="Automatically set from model; leave None for auto-detection"
    )

# ------------------------------------------------------------------------------
# CodeMatcher Class
# ------------------------------------------------------------------------------
class CodeMatcher:
    """
    Advanced multilingual code matcher using PostgreSQL + pgvector.
    Automatically detects language, uses multilingual embeddings,
    and performs cosine similarity search with strict threshold.
    """

    def __init__(self, config: Optional[CodeMatcherConfig] = None):
        """
        Initialize the CodeMatcher.

        Args:
            config: Configuration override; if None, reads from environment.
        """
        self.config = config or CodeMatcherConfig()
        self.similarity_threshold = self.config.similarity_threshold

        # Validate embedding model availability
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for embeddings. "
                "Install with: pip install sentence-transformers"
            )

        # Load embedding model
        logger.info(f"Loading embedding model: {self.config.embedding_model_name}")
        self._embedding_model = SentenceTransformer(self.config.embedding_model_name)

        # Determine vector dimension from model
        if self.config.vector_dimension is None:
            # Get dimension by encoding a sample text
            sample_vector = self._embedding_model.encode("test", normalize_embeddings=True)
            self.vector_dimension = len(sample_vector)
        else:
            self.vector_dimension = self.config.vector_dimension

        logger.info(f"Vector dimension: {self.vector_dimension}")

        # Initialize connection pool
        self._pool = None
        self._initialize_pool()

        # Ensure schema exists
        self._ensure_schema()

        # Language detection fallback
        self._default_lang = "en"

        logger.info(f"CodeMatcher initialized with threshold {self.similarity_threshold}, "
                    f"model {self.config.embedding_model_name}")

    def _initialize_pool(self) -> None:
        """Initialize the PostgreSQL connection pool."""
        try:
            self._pool = SimpleConnectionPool(
                self.config.pool_min_conn,
                self.config.pool_max_conn,
                host=self.config.db_host,
                port=self.config.db_port,
                dbname=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
            )
            logger.info("Database connection pool created.")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _get_connection(self) -> PsycopgConnection:
        """Get a connection from the pool."""
        if self._pool is None:
            self._initialize_pool()
        return self._pool.getconn()

    def _release_connection(self, conn: PsycopgConnection) -> None:
        """Release connection back to the pool."""
        if self._pool is not None:
            self._pool.putconn(conn)

    def _ensure_schema(self) -> None:
        """Create the necessary schema if it doesn't exist."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                # Create table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS codes (
                        id SERIAL PRIMARY KEY,
                        section TEXT NOT NULL,
                        full_text TEXT NOT NULL,
                        source TEXT NOT NULL,
                        language TEXT,
                        vector vector(%s)
                    );
                """, (self.vector_dimension,))
                # Create index for cosine similarity search
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS codes_vector_idx ON codes 
                    USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
                """)
                conn.commit()
                logger.info("Schema verified/created.")
        except Exception as e:
            logger.error(f"Schema creation failed: {e}")
            raise
        finally:
            self._release_connection(conn)

    def _detect_language(self, text: str) -> str:
        """Detect language of a text with fallback."""
        if not LANGDETECT_AVAILABLE:
            return self._default_lang
        try:
            lang = detect(text)
            return lang if lang else self._default_lang
        except Exception:
            return self._default_lang

    def _encode_text(self, text: str, normalize: bool = True) -> List[float]:
        """Encode text to a vector using the multilingual model."""
        try:
            vector = self._embedding_model.encode(text, normalize_embeddings=normalize)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            raise

    def ingest_code_entry(self, entry: CodeEntry) -> int:
        """
        Insert a single code entry with its vector.

        Args:
            entry: CodeEntry object.

        Returns:
            The ID of the inserted row.
        """
        # Ensure language field is set
        if entry.language is None:
            entry.language = self._detect_language(entry.full_text)

        # Generate vector from full_text
        vector = self._encode_text(entry.full_text)
        if len(vector) != self.vector_dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.vector_dimension}, got {len(vector)}")

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                vector_str = '[' + ','.join(str(v) for v in vector) + ']'
                cur.execute(
                    sql.SQL("INSERT INTO codes (section, full_text, source, language, vector) VALUES (%s, %s, %s, %s, %s) RETURNING id;"),
                    (entry.section, entry.full_text, entry.source, entry.language, vector_str)
                )
                inserted_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Ingested code entry: {entry.section} (lang: {entry.language}) with ID {inserted_id}")
                return inserted_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to ingest code entry: {e}")
            raise
        finally:
            self._release_connection(conn)

    def ingest_batch(self, entries: List[CodeEntry]) -> List[int]:
        """
        Insert multiple code entries in batch.

        Args:
            entries: List of CodeEntry objects.

        Returns:
            List of inserted IDs.
        """
        inserted_ids = []
        for entry in entries:
            try:
                id_ = self.ingest_code_entry(entry)
                inserted_ids.append(id_)
            except Exception as e:
                logger.error(f"Failed to ingest entry {entry.section}: {e}")
                # Continue with others
        return inserted_ids

    def match_vector(self, query_vector: List[float], limit: int = 5) -> List[CodeMatchResult]:
        """
        Perform cosine similarity search against the codes table.

        Args:
            query_vector: Query embedding vector.
            limit: Maximum number of results.

        Returns:
            List of CodeMatchResult objects sorted by similarity descending.
        """
        if len(query_vector) != self.vector_dimension:
            raise ValueError(f"Query vector dimension mismatch: expected {self.vector_dimension}, got {len(query_vector)}")

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                vector_str = '[' + ','.join(str(v) for v in query_vector) + ']'
                # Cosine similarity = 1 - cosine_distance
                cur.execute(
                    """
                    SELECT section, full_text, source, 
                           1 - (vector <=> %s::vector) AS similarity
                    FROM codes
                    WHERE 1 - (vector <=> %s::vector) >= %s
                    ORDER BY similarity DESC
                    LIMIT %s;
                    """,
                    (vector_str, vector_str, self.similarity_threshold, limit)
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    section, full_text, source, similarity = row
                    results.append(CodeMatchResult(
                        section=section,
                        full_text=full_text,
                        source=source,
                        similarity_score=float(similarity),
                        is_match=similarity >= self.similarity_threshold
                    ))
                return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise
        finally:
            self._release_connection(conn)

    def match_text(
        self,
        text: str,
        limit: int = 5,
        auto_detect_language: bool = True
    ) -> List[CodeMatchResult]:
        """
        Convenience method: detect language, encode text, then search.

        Args:
            text: Input text to match.
            limit: Max results.
            auto_detect_language: If True, detect language (for logging).

        Returns:
            List of CodeMatchResult.
        """
        try:
            if auto_detect_language:
                lang = self._detect_language(text)
                logger.info(f"Detected language: {lang}")
            vector = self._encode_text(text)
            return self.match_vector(vector, limit)
        except Exception as e:
            logger.error(f"Text matching failed: {e}")
            raise

    def match_text_with_language(
        self,
        text: str,
        target_language: Optional[str] = None,
        limit: int = 5
    ) -> List[CodeMatchResult]:
        """
        Match text, optionally filtering results by language of the code entries.
        This uses a metadata filter if we extend the query.
        For now, we just do normal match and filter in post-processing if needed.
        """
        # For simplicity, we just call match_text; language filtering could be added.
        return self.match_text(text, limit)

    def clear_all_entries(self) -> None:
        """Clear all code entries (for testing or re‑ingestion)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE codes RESTART IDENTITY;")
                conn.commit()
                logger.info("All code entries cleared.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to clear entries: {e}")
            raise
        finally:
            self._release_connection(conn)

    def get_entry_count(self) -> int:
        """Return number of entries in the codes table."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM codes;")
                count = cur.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Failed to get entry count: {e}")
            return 0
        finally:
            self._release_connection(conn)

    def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None
            logger.info("Database connection pool closed.")

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Example embedding function (actual model used)
    matcher = CodeMatcher()

    # Example entries in different languages
    entries = [
        CodeEntry(
            section="IBC 1006.2.1",
            full_text="Egress doors shall have a minimum clear width of 32 inches.",
            source="International Building Code 2021"
        ),
        CodeEntry(
            section="NFPA 101 7.2.1",
            full_text="Door openings shall provide a clear width of at least 32 inches.",
            source="NFPA Life Safety Code 2021"
        ),
        CodeEntry(
            section="Código de Edificación de España CTE DB-SI",
            full_text="Las puertas de salida deben tener un ancho mínimo de 0.80 m.",
            source="Código Técnico de la Edificación (CTE) - Seguridad en caso de incendio",
            language="es"
        ),
        CodeEntry(
            section="NFPA 101 7.2.1 (French)",
            full_text="Les portes de sortie doivent avoir une largeur libre minimale de 32 pouces.",
            source="Code de sécurité NFPA 101",
            language="fr"
        ),
    ]
    for entry in entries:
        matcher.ingest_code_entry(entry)

    # Search in English
    query_en = "door width minimum 32 inches"
    results_en = matcher.match_text(query_en, limit=3)
    print("\nEnglish query results:")
    for r in results_en:
        print(f"  {r.section}: {r.full_text} (score: {r.similarity_score:.3f})")

    # Search in Spanish
    query_es = "ancho mínimo de puerta de salida 0.80 m"
    results_es = matcher.match_text(query_es, limit=3)
    print("\nSpanish query results:")
    for r in results_es:
        print(f"  {r.section}: {r.full_text} (score: {r.similarity_score:.3f})")

    matcher.close()
