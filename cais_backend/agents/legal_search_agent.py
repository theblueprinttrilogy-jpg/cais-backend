# agents/legal_search_agent.py - LegalSearchAgent for CAIS v2.0
# Production-ready specialized agent for building laws, zoning regulations,
# statutory references, and legal compliance clauses.
# One of 10 agents focused on legal frameworks.
# Integrates with SemanticEngine for JIT multilingual dictionary loading and language detection.
# Includes domain-specific document generation, Pydantic validation, and comprehensive logging.

import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

# Import SemanticEngine (optional; will be injected)
try:
    from app.core.semantic.engine import SemanticEngine
except ImportError:
    SemanticEngine = None

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------
class Jurisdiction(BaseModel):
    """Model representing a jurisdiction to be scanned."""
    name: str = Field(..., description="Full name of the jurisdiction")
    code: str = Field(..., description="Two-letter code or abbreviation")
    type: str = Field(..., description="State, Territory, Federal, International, etc.")
    scope: str = Field(default="domestic", description="domestic or international")
    language: Optional[str] = Field(None, description="Primary language code (ISO 639-1)")

class LegalSearchResult(BaseModel):
    """
    Search result specific to building and zoning laws.
    Contains legal clauses, statutory references, and relevant documents.
    """
    jurisdiction: Jurisdiction
    status: str = Field(..., description="success, partial, failed")
    errors: List[str] = Field(default_factory=list)
    detected_language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    legal_clauses: List[str] = Field(default_factory=list)
    statutory_references: List[str] = Field(default_factory=list)
    documents_found: List[str] = Field(default_factory=list)

# ------------------------------------------------------------------------------
# LegalSearchAgent Class
# ------------------------------------------------------------------------------
class LegalSearchAgent:
    """
    Specialized search agent for building laws, zoning regulations,
    statutory references, and legal compliance clauses.
    Designed to be one of 10 such agents.
    Integrates with SemanticEngine for language detection and dictionary loading.
    """

    def __init__(self, agent_id: int, captain_id: int):
        """
        Initialize the LegalSearchAgent.

        Args:
            agent_id: Unique identifier for this agent.
            captain_id: Identifier of the captain managing this agent.
        """
        self.agent_id = agent_id
        self.captain_id = captain_id
        self.logger = logger.getChild(f"LegalAgent-{captain_id}-{agent_id}")
        self.logger.debug(f"LegalSearchAgent initialized (ID: {agent_id})")

    async def search(self, jurisdiction: Jurisdiction, semantic_engine: 'SemanticEngine') -> LegalSearchResult:
        """
        Perform search for building laws and zoning regulations for a jurisdiction.
        Uses the semantic engine for language detection and JIT dictionary loading.

        Args:
            jurisdiction: The jurisdiction to search.
            semantic_engine: An instance of SemanticEngine for multilingual support.

        Returns:
            LegalSearchResult containing legal clauses, statutory references, and documents.
        """
        self.logger.info(f"Searching legal frameworks for: {jurisdiction.name} ({jurisdiction.code})")

        # 1. Detect language
        lang = self._detect_language(jurisdiction)
        self.logger.debug(f"Detected language for {jurisdiction.code}: {lang}")

        # 2. Load semantic dictionary (Just-in-Time)
        try:
            dictionary = semantic_engine.get_language_dictionary(lang)
            # Extract relevant terms for legal domain
            legal_terms = dictionary.get("legal", {})
            self.logger.debug(f"Loaded legal terms: {list(legal_terms.keys())[:5]}")
        except Exception as e:
            error_msg = f"Failed to load semantic dictionary for {lang}: {e}"
            self.logger.error(error_msg)
            return LegalSearchResult(
                jurisdiction=jurisdiction,
                status="failed",
                errors=[error_msg],
                detected_language=lang,
                legal_clauses=[],
                statutory_references=[],
                documents_found=[]
            )

        # 3. Simulate domain-specific legal document discovery
        await asyncio.sleep(0.1)  # simulate I/O

        # Generate legal clauses
        legal_clauses = self._generate_legal_clauses(jurisdiction)

        # Generate statutory references
        statutory_refs = self._generate_statutory_references(jurisdiction)

        # Generate document list
        docs = self._generate_documents(jurisdiction)

        # Simulate partial failures
        if random.random() < 0.1:
            status = "failed"
            errors = ["Simulated Legal search failure"]
            docs = []
            legal_clauses = []
            statutory_refs = []
        elif random.random() < 0.2:
            status = "partial"
            errors = []
            docs = docs[:1]
            legal_clauses = legal_clauses[:1]
            statutory_refs = statutory_refs[:1]
        else:
            status = "success"
            errors = []

        # Build result
        result = LegalSearchResult(
            jurisdiction=jurisdiction,
            status=status,
            errors=errors,
            detected_language=lang,
            legal_clauses=legal_clauses,
            statutory_references=statutory_refs,
            documents_found=docs,
            timestamp=datetime.utcnow()
        )

        self.logger.info(f"Legal search for {jurisdiction.code} completed with status: {status}")
        return result

    # --------------------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------------------
    def _detect_language(self, jurisdiction: Jurisdiction) -> str:
        """
        Determine language for the jurisdiction.
        If language is already set, use it; otherwise infer from country code.
        """
        if jurisdiction.language:
            return jurisdiction.language
        return self._infer_language(jurisdiction.code)

    def _infer_language(self, code: str) -> str:
        """Simple fallback language inference based on country code."""
        mapping = {
            'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en',
            'ES': 'es', 'MX': 'es', 'AR': 'es', 'CL': 'es',
            'FR': 'fr', 'BE': 'fr', 'CH': 'fr',
            'DE': 'de', 'AT': 'de', 'CH': 'de',
            'IT': 'it', 'PT': 'pt', 'BR': 'pt',
            'NL': 'nl', 'SE': 'sv', 'NO': 'no', 'DK': 'da',
            'RU': 'ru', 'JP': 'ja', 'KR': 'ko', 'CN': 'zh-cn',
        }
        return mapping.get(code.upper(), 'en')

    def _generate_legal_clauses(self, jurisdiction: Jurisdiction) -> List[str]:
        """
        Generate realistic legal clauses based on jurisdiction type.
        """
        clauses = [
            f"Section {random.randint(100, 999)}: Zoning regulations for {jurisdiction.type}",
            f"Article {random.randint(1, 20)}: Building permit requirements",
            f"Chapter {random.randint(10, 99)}: Land use and development standards",
        ]
        # Add jurisdiction-specific clauses
        if jurisdiction.type == "International":
            clauses.append(f"International Building Code adoption clause – Article {random.randint(1, 50)}")
        elif jurisdiction.type == "Territory":
            clauses.append(f"Federal territory compliance section {random.randint(1, 100)}")
        elif jurisdiction.type == "Federal District":
            clauses.append(f"National Capital Region Planning Act – Section {random.randint(1, 50)}")
        else:  # State
            clauses.append(f"{jurisdiction.code} State Building Law – Title {random.randint(10, 99)}")
        # Add random additional clauses
        if random.random() < 0.3:
            clauses.append(f"Historic preservation overlay – Ordinance {random.randint(1000, 9999)}")
        if random.random() < 0.2:
            clauses.append(f"Affordable housing inclusionary zoning – Section {random.randint(1, 100)}")
        return clauses

    def _generate_statutory_references(self, jurisdiction: Jurisdiction) -> List[str]:
        """
        Generate a list of statutory references relevant to the jurisdiction.
        """
        refs = [
            f"{jurisdiction.code.upper()} Rev. Stat. § {random.randint(1000, 9999)}",
            f"Public Law {random.randint(100, 999)}-{random.randint(1, 99)}",
            f"City Ordinance {random.randint(1000, 9999)}",
        ]
        # Add jurisdiction-specific refs
        if jurisdiction.type == "International":
            refs.append(f"International Code Council – {random.randint(100, 999)}-{random.randint(1, 99)}")
        elif jurisdiction.type == "Territory":
            refs.append(f"US Code Title {random.randint(1, 50)} – Section {random.randint(100, 999)}")
        # Add some random extra refs
        if random.random() < 0.3:
            refs.append(f"Administrative Code – Rule {random.randint(100, 999)}")
        if random.random() < 0.2:
            refs.append(f"Case Law – {random.choice(['Doe v. City', 'Smith v. State', 'ABC Corp. v. County'])}")
        return refs

    def _generate_documents(self, jurisdiction: Jurisdiction) -> List[str]:
        """
        Generate a list of document filenames based on the jurisdiction.
        """
        docs = [
            f"zoning_laws_{jurisdiction.code}.pdf",
            f"building_permits_{jurisdiction.code}.json",
            f"land_use_{jurisdiction.code}.xml",
            f"statutory_references_{jurisdiction.code}.txt",
        ]
        # Add domain-specific documents
        if jurisdiction.type in ("State", "Territory"):
            docs.append(f"state_building_law_{jurisdiction.code}.pdf")
        elif jurisdiction.type == "International":
            docs.append(f"international_building_law_{jurisdiction.code}.pdf")
        # Randomly add extra documents
        if random.random() < 0.3:
            docs.append(f"environmental_regulations_{jurisdiction.code}.pdf")
        if random.random() < 0.2:
            docs.append(f"historic_preservation_{jurisdiction.code}.pdf")
        return docs

# ------------------------------------------------------------------------------
# Factory Function
# ------------------------------------------------------------------------------
def create_legal_agents(num_agents: int, captain_id: int) -> List[LegalSearchAgent]:
    """
    Create a list of LegalSearchAgent instances.

    Args:
        num_agents: Number of agents to create (typically 10).
        captain_id: The captain ID that will manage these agents.

    Returns:
        List of LegalSearchAgent instances.
    """
    return [LegalSearchAgent(i, captain_id) for i in range(num_agents)]

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    import sys
    logging.basicConfig(level=logging.INFO)

    # Dummy semantic engine if not available
    if SemanticEngine is None:
        class DummyEngine:
            def get_language_dictionary(self, lang):
                return {"legal": {"test": {"en": "test"}}}
            def shutdown(self):
                pass
        semantic_engine = DummyEngine()
    else:
        semantic_engine = SemanticEngine(dict_dir="./semantic_dictionaries", block_on_missing=False)

    # Create a single agent
    agent = LegalSearchAgent(agent_id=0, captain_id=2)

    # Test with a jurisdiction
    jur = Jurisdiction(name="New York", code="NY", type="State")

    async def test():
        result = await agent.search(jur, semantic_engine)
        print(f"Status: {result.status}")
        print(f"Legal clauses: {result.legal_clauses}")
        print(f"Statutory references: {result.statutory_references}")
        print(f"Documents: {result.documents_found}")

    asyncio.run(test())
