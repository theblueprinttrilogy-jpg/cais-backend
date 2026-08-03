"""
app/agents/orchestrator.py

Autonomous Orchestrator for CAIS Code Compliance backend.
Manages ingestion tasks, coordinates Captains and Search Agents,
and delegates persistence to Storage Agents with vector embeddings.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, create_engine, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database setup – use environment variable or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/cais_code_db"
)
engine = None
SessionLocal = None
Base = declarative_base()


class CodeReference(Base):
    """SQLAlchemy model for the code_references table."""
    __tablename__ = "code_references"

    id = Column(Integer, primary_key=True, index=True)
    section = Column(String(255), nullable=False)
    title = Column(String(500))
    description = Column(Text)
    full_text = Column(Text)
    jurisdiction = Column(String(100), nullable=False)
    code_type = Column(String(100), nullable=False)
    severity = Column(String(50))
    embedding = Column(Vector(384))  # all-MiniLM-L6-v2 produces 384-dim vectors

    # Unique constraint to enforce uniqueness per section, jurisdiction, code_type
    __table_args__ = (
        UniqueConstraint('section', 'jurisdiction', 'code_type',
                         name='uq_section_jurisdiction_code_type'),
    )


def initialize_database(max_retries: int = 5, retry_delay: int = 3) -> None:
    """
    Initialize the database connection, enable extensions, and create tables.
    Retries on connection failures up to max_retries times with a delay between attempts.

    :param max_retries: Maximum number of connection attempts.
    :param retry_delay: Seconds to wait between retries.
    :raises: Exception if all retries fail.
    """
    global engine, SessionLocal

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Database initialization attempt {attempt}/{max_retries}...")
            # Create engine
            engine = create_engine(DATABASE_URL)
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("Database connection established.")

            # Enable required extensions
            extensions = ["vector", "pgcrypto"]
            with engine.connect() as conn:
                for ext in extensions:
                    try:
                        conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext};"))
                        conn.commit()
                        logger.info(f"PostgreSQL extension '{ext}' enabled successfully.")
                    except Exception as e:
                        logger.error(f"Failed to enable extension '{ext}': {e}")
                        # Continue with other extensions; we still might proceed
                        # but if vector fails, pgvector will not work.
                        # We'll re-raise if vector fails because it's critical.
                        if ext == "vector":
                            raise

            # Create tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully.")

            # Set up session factory
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            logger.info("Database initialization complete.")
            return  # Success

        except Exception as e:
            logger.error(f"Database initialization attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.critical("All database initialization attempts failed.")
                raise  # Re-raise the last exception


# Initialize database with retries at module import
try:
    initialize_database()
except Exception:
    logger.critical("Unable to initialize database. Application may not function correctly.")
    # Continue anyway; the app might still work if tables exist already, but we log.


class StorageAgent:
    """
    Storage Agent responsible for embedding generation and persistence
    of code reference records into PostgreSQL using pgvector.
    Uses standard SQLAlchemy add/commit with check‑then‑insert/update logic.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the Storage Agent with a sentence transformer model.

        :param model_name: Name of the SentenceTransformer model to use.
        """
        logger.info(f"Initializing StorageAgent with model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for the given text.

        :param text: Raw text to embed.
        :return: List of floats representing the embedding vector.
        """
        if not text or not text.strip():
            # For empty text, use a zero vector of appropriate length
            return [0.0] * 384
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def store_code_reference(
        self,
        section: str,
        title: str,
        description: str,
        full_text: str,
        jurisdiction: str,
        code_type: str,
        severity: str,
    ) -> CodeReference:
        """
        Generate embedding from the combined text and store the record
        into the code_references table using standard SQLAlchemy operations.

        The embedding is generated from a concatenation of section, title,
        description, and full_text (with appropriate separators).

        :param section: Code section identifier.
        :param title: Title of the code reference.
        :param description: Brief description.
        :param full_text: Full legal text.
        :param jurisdiction: Jurisdiction (e.g., "US", "CA").
        :param code_type: Type of code (e.g., "building", "fire").
        :param severity: Severity level (e.g., "high", "medium", "low").
        :return: The inserted/updated CodeReference instance.
        """
        logger.info(
            f"StorageAgent: Storing reference for section={section}, "
            f"jurisdiction={jurisdiction}, code_type={code_type}"
        )

        # Build the text to embed from the combined fields
        combined_text = " ".join(
            filter(None, [
                section,
                title,
                description,
                full_text
            ])
        )
        embedding_vector = self._generate_embedding(combined_text)

        if SessionLocal is None:
            raise RuntimeError("Database session factory not initialized.")

        session = SessionLocal()
        try:
            # Check if a record with the same unique key already exists
            existing = session.query(CodeReference).filter_by(
                section=section,
                jurisdiction=jurisdiction,
                code_type=code_type
            ).first()

            if existing:
                # Update the existing record
                existing.title = title
                existing.description = description
                existing.full_text = full_text
                existing.severity = severity
                existing.embedding = embedding_vector
                logger.info(f"StorageAgent: Updated existing record ID={existing.id}")
            else:
                # Create a new record
                new_record = CodeReference(
                    section=section,
                    title=title,
                    description=description,
                    full_text=full_text,
                    jurisdiction=jurisdiction,
                    code_type=code_type,
                    severity=severity,
                    embedding=embedding_vector,
                )
                session.add(new_record)
                logger.info("StorageAgent: Created new record")

            session.commit()

            # Retrieve the final record (existing or new)
            record = session.query(CodeReference).filter_by(
                section=section,
                jurisdiction=jurisdiction,
                code_type=code_type
            ).first()

            logger.info(
                f"StorageAgent: Successfully stored reference ID={record.id if record else 'unknown'}"
            )
            return record

        except Exception as e:
            session.rollback()
            logger.error(f"StorageAgent: Database error: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """No persistent session to close; kept for API consistency."""
        logger.info("StorageAgent: No open sessions to close.")


class SearchAgent:
    """
    Simulated Search Agent that retrieves code reference data from various sources.
    In a real implementation, this would interface with external APIs, document stores,
    or web scraping.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform a search and return a list of raw code reference dictionaries.

        :param query: Search query string.
        :return: List of dictionaries with keys:
                 section, title, description, full_text, jurisdiction, code_type, severity.
        """
        logger.info(f"SearchAgent[{self.source_name}]: Searching for '{query}'")
        # Simulate retrieval with dummy data
        # In a real system, this would fetch and parse real data.
        dummy_results = [
            {
                "section": "101.1",
                "title": "General Provisions",
                "description": "Scope and applicability of the code.",
                "full_text": "This code shall apply to all buildings...",
                "jurisdiction": "US",
                "code_type": "building",
                "severity": "medium",
            },
            {
                "section": "202.5",
                "title": "Fire Safety",
                "description": "Requirements for fire suppression systems.",
                "full_text": "Fire sprinklers shall be installed in all...",
                "jurisdiction": "US",
                "code_type": "fire",
                "severity": "high",
            },
        ]
        # Optionally filter by query (very basic simulation)
        if query:
            filtered = [r for r in dummy_results if query.lower() in r["section"].lower()
                        or query.lower() in r["title"].lower()]
            if filtered:
                return filtered
        return dummy_results[:1]  # return first dummy result as default


class Captain:
    """
    Simulated Captain agent that orchestrates the ingestion workflow.
    It decides which Search Agents to invoke and aggregates their results.
    """

    def __init__(self, search_agents: List[SearchAgent]):
        self.search_agents = search_agents

    def delegate(self, query: str) -> List[Dict[str, Any]]:
        """
        Delegate the search task to all registered Search Agents and
        collect their results.

        :param query: Search query.
        :return: Aggregated list of raw code reference dictionaries.
        """
        logger.info(f"Captain: Delegating search for '{query}' to {len(self.search_agents)} agents.")
        all_results = []
        for agent in self.search_agents:
            results = agent.search(query)
            all_results.extend(results)
        logger.info(f"Captain: Collected {len(all_results)} results from agents.")
        return all_results


class AutonomousOrchestrator:
    """
    Main orchestrator for code compliance ingestion.
    Manages the entire pipeline: Captain delegation, Search Agent retrieval,
    and Storage Agent persistence with vector embeddings.
    """

    def __init__(
        self,
        captain: Optional[Captain] = None,
        storage_agent: Optional[StorageAgent] = None,
    ):
        """
        Initialize the orchestrator with a Captain and a Storage Agent.
        If not provided, default components are created with simulated Search Agents.

        :param captain: Captain instance (or None to create default).
        :param storage_agent: StorageAgent instance (or None to create default).
        """
        logger.info("Initializing AutonomousOrchestrator.")

        if captain is None:
            # Create a default Captain with a set of simulated Search Agents
            search_agents = [
                SearchAgent("WebScraper"),
                SearchAgent("InternalDB"),
            ]
            self.captain = Captain(search_agents)
            logger.info("Default Captain created with 2 simulated Search Agents.")
        else:
            self.captain = captain

        if storage_agent is None:
            self.storage_agent = StorageAgent()
            logger.info("Default StorageAgent created.")
        else:
            self.storage_agent = storage_agent

        logger.info("AutonomousOrchestrator initialization complete.")

    def ingest(self, query: str) -> List[CodeReference]:
        """
        Perform a complete ingestion cycle:
          1. Captain delegates the query to Search Agents.
          2. For each retrieved reference, the Storage Agent stores it.
          3. Return the list of persisted CodeReference objects.

        :param query: The search/ingestion query.
        :return: List of stored CodeReference instances.
        """
        logger.info(f"Orchestrator: Starting ingestion for query: '{query}'")

        # Phase 1: Captain delegation
        logger.info("Orchestrator: Phase 1 - Captain delegation.")
        raw_references = self.captain.delegate(query)

        if not raw_references:
            logger.warning("Orchestrator: No references returned by Captain. Ingestion aborted.")
            return []

        # Phase 2: Storage Agent persistence
        logger.info(f"Orchestrator: Phase 2 - Storing {len(raw_references)} references.")
        stored_records = []
        for idx, ref in enumerate(raw_references, 1):
            logger.info(f"Orchestrator: Processing reference #{idx}.")
            try:
                record = self.storage_agent.store_code_reference(
                    section=ref.get("section", ""),
                    title=ref.get("title", ""),
                    description=ref.get("description", ""),
                    full_text=ref.get("full_text", ""),
                    jurisdiction=ref.get("jurisdiction", ""),
                    code_type=ref.get("code_type", ""),
                    severity=ref.get("severity", ""),
                )
                stored_records.append(record)
                logger.info(f"Orchestrator: Reference #{idx} stored successfully.")
            except Exception as e:
                logger.error(f"Orchestrator: Failed to store reference #{idx}: {e}")
                # Continue with next reference; optionally raise or handle differently

        logger.info(f"Orchestrator: Ingestion completed. Stored {len(stored_records)} records.")
        return stored_records

    def close(self):
        """Clean up resources (close storage agent sessions, etc.)."""
        if self.storage_agent:
            self.storage_agent.close()
        logger.info("Orchestrator: Resources closed.")


# Example usage (for testing)
if __name__ == "__main__":
    # This block can be used for manual testing
    orchestrator = AutonomousOrchestrator()
    try:
        results = orchestrator.ingest("fire safety")
        print(f"Ingested {len(results)} records.")
        for rec in results:
            print(f"ID: {rec.id}, Section: {rec.section}, Jurisdiction: {rec.jurisdiction}")
    finally:
        orchestrator.close()
