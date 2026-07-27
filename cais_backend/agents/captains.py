# agents/captains.py - Captain and Search Agent module for CAIS v2.0
# Production-ready module defining the Captain and SearchAgent classes.
# Manages pools of search agents for discovering construction codes, safety regulations,
# and building laws across jurisdictions. Integrates with the SemanticEngine for
# multilingual support and language detection.

import asyncio
import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

# Import semantic engine if available; we'll accept it as a dependency.
# We'll avoid hard dependency to keep module flexible.
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

class SearchResult(BaseModel):
    """Model for search results from a jurisdiction."""
    jurisdiction: Jurisdiction
    status: str = Field(..., description="success, partial, failed")
    documents_found: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    detected_language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ------------------------------------------------------------------------------
# Search Agent
# ------------------------------------------------------------------------------
class SearchAgent:
    """
    A search agent responsible for discovering documents for a single jurisdiction.
    Uses the SemanticEngine for language detection and dictionary loading.
    """

    def __init__(self, agent_id: int, captain_id: int):
        """
        Initialize the search agent.

        Args:
            agent_id: Unique identifier for this agent.
            captain_id: Identifier of the captain managing this agent.
        """
        self.agent_id = agent_id
        self.captain_id = captain_id
        self.logger = logger.getChild(f"SearchAgent-{captain_id}-{agent_id}")

    async def search(self, jurisdiction: Jurisdiction, semantic_engine: 'SemanticEngine') -> SearchResult:
        """
        Perform the search for a jurisdiction, using the semantic engine for
        language detection and dictionary loading (Just-in-Time).

        Args:
            jurisdiction: The jurisdiction to search.
            semantic_engine: An instance of SemanticEngine for language support.

        Returns:
            SearchResult containing discovered documents and status.
        """
        self.logger.info(f"Searching jurisdiction: {jurisdiction.name} ({jurisdiction.code})")

        # 1. Detect language if not already set
        detected_lang = jurisdiction.language or self._infer_language(jurisdiction.code)

        # 2. Load semantic dictionary (Just-in-Time) - triggers lazy loading
        try:
            dictionary = semantic_engine.get_language_dictionary(detected_lang)
            self.logger.debug(f"Loaded dictionary for {detected_lang} with keys: {list(dictionary.get('construction', {}).keys())[:5]}")
        except Exception as e:
            self.logger.error(f"Failed to load semantic dictionary for {detected_lang}: {e}")
            return SearchResult(
                jurisdiction=jurisdiction,
                status="failed",
                errors=[f"Dictionary load error: {str(e)}"],
                detected_language=detected_lang
            )

        # 3. Simulate document discovery (real implementation would use web/API)
        # For simulation, we generate documents based on jurisdiction code.
        # In production, replace with actual scraping or API calls.
        await asyncio.sleep(0.1)  # simulate network I/O

        docs = [
            f"building_code_{jurisdiction.code}_2025.pdf",
            f"safety_regulations_{jurisdiction.code}.xml",
            f"zoning_laws_{jurisdiction.code}.json",
            f"fire_safety_{jurisdiction.code}.pdf",
        ]
        # Simulate occasional failures or partial results
        if random.random() < 0.1:
            docs = []
            status = "failed"
            errors = ["Simulated search failure"]
        elif random.random() < 0.2:
            docs = docs[:2]
            status = "partial"
            errors = []
        else:
            status = "success"
            errors = []

        return SearchResult(
            jurisdiction=jurisdiction,
            status=status,
            documents_found=docs,
            errors=errors,
            detected_language=detected_lang
        )

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

# ------------------------------------------------------------------------------
# Captain
# ------------------------------------------------------------------------------
class Captain:
    """
    A Captain manages a pool of SearchAgents and distributes jurisdictions among them.
    It collects results and handles concurrency via a semaphore.
    """

    def __init__(self, captain_id: int, num_agents: int):
        """
        Initialize a Captain with a given number of search agents.

        Args:
            captain_id: Unique identifier for this captain.
            num_agents: Number of SearchAgent instances to manage.
        """
        self.captain_id = captain_id
        self.agents = [SearchAgent(i, captain_id) for i in range(num_agents)]
        self.logger = logger.getChild(f"Captain-{captain_id}")

    async def process_jurisdictions(
        self,
        jurisdictions: List[Jurisdiction],
        semantic_engine: 'SemanticEngine',
        semaphore: asyncio.Semaphore
    ) -> List[SearchResult]:
        """
        Distribute jurisdictions among the agents, respecting concurrency limits.

        Args:
            jurisdictions: List of Jurisdiction objects to process.
            semantic_engine: An instance of SemanticEngine for language support.
            semaphore: Asyncio semaphore to limit concurrent tasks.

        Returns:
            List of SearchResult objects from all agents.
        """
        self.logger.info(f"Processing {len(jurisdictions)} jurisdictions with {len(self.agents)} agents.")
        tasks = []
        for idx, jur in enumerate(jurisdictions):
            agent = self.agents[idx % len(self.agents)]
            tasks.append(self._run_search_with_semaphore(agent, jur, semantic_engine, semaphore))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and convert to SearchResult where needed
        valid_results = []
        for idx, r in enumerate(results):
            if isinstance(r, SearchResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                self.logger.error(f"Search task for {jurisdictions[idx].name} failed: {r}")
                # Create a failed result
                valid_results.append(SearchResult(
                    jurisdiction=jurisdictions[idx],
                    status="failed",
                    errors=[f"Task error: {str(r)}"]
                ))
        return valid_results

    async def _run_search_with_semaphore(
        self,
        agent: SearchAgent,
        jurisdiction: Jurisdiction,
        semantic_engine: 'SemanticEngine',
        semaphore: asyncio.Semaphore
    ) -> SearchResult:
        """Run a single agent search with semaphore control."""
        async with semaphore:
            return await agent.search(jurisdiction, semantic_engine)

# ------------------------------------------------------------------------------
# Captain Factory
# ------------------------------------------------------------------------------
def create_captains(num_captains: int, agents_per_captain: int) -> List[Captain]:
    """
    Factory function to create a list of Captains.

    Args:
        num_captains: Number of Captain instances.
        agents_per_captain: Number of SearchAgent instances per Captain.

    Returns:
        List of Captain instances.
    """
    return [Captain(i, agents_per_captain) for i in range(num_captains)]

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    import sys
    logging.basicConfig(level=logging.INFO)

    # Create a dummy semantic engine if not available
    if SemanticEngine is None:
        class DummyEngine:
            def get_language_dictionary(self, lang):
                return {"construction": {"test": {"en": "test"}}}
            def shutdown(self):
                pass
        semantic_engine = DummyEngine()
    else:
        semantic_engine = SemanticEngine(dict_dir="./semantic_dictionaries", block_on_missing=False)

    # Create captains
    captains = create_captains(3, 10)
    jurisdictions = [
        Jurisdiction(name="California", code="CA", type="State"),
        Jurisdiction(name="New York", code="NY", type="State"),
        Jurisdiction(name="Texas", code="TX", type="State"),
        Jurisdiction(name="District of Columbia", code="DC", type="Federal District"),
    ]

    semaphore = asyncio.Semaphore(10)

    async def run_test():
        tasks = []
        for cap in captains:
            # Each captain processes a subset
            tasks.append(cap.process_jurisdictions(jurisdictions, semantic_engine, semaphore))
        all_results = await asyncio.gather(*tasks)
        for res in all_results:
            for r in res:
                print(f"{r.jurisdiction.name}: {r.status} ({len(r.documents_found)} docs)")
        semantic_engine.shutdown()

    asyncio.run(run_test())
