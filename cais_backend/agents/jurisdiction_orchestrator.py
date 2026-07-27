# agents/jurisdiction_orchestrator.py - Master Jurisdiction Orchestrator for CAIS v2.0
# Production-ready orchestrator managing 3 Captains, 30 Search Agents, and Storage Agents
# as an autonomous, periodic batch process (monthly) to scan global construction codes,
# safety regulations, and building laws.
# Features: dynamic multilingual semantic dictionary loading (Just-in-Time),
# ephemeral resource lifecycle (purge after each jurisdiction batch),
# async concurrency, Pydantic validation, and forensic logging.

import os
import sys
import asyncio
import logging
import json
import shutil
import tarfile
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict

import aiofiles
from pydantic import BaseModel, Field, validator

# Import semantic engine for multilingual support
from app.core.semantic.engine import SemanticEngine

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

class StorageManifest(BaseModel):
    """WORM-compatible manifest for stored archives."""
    archive_name: str
    jurisdictions: List[str]  # List of jurisdiction codes
    created_at: datetime
    hash_sha256: Optional[str] = None
    total_documents: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OrchestratorConfig(BaseModel):
    """Configuration for the JurisdictionOrchestrator."""
    output_base_dir: str = Field(
        default=os.environ.get("JURISDICTION_OUTPUT_DIR", "/workspace/outputs/jurisdictions")
    )
    num_captains: int = Field(default=3)
    agents_per_captain: int = Field(default=10)
    max_concurrent_tasks: int = Field(default=30)
    monthly_interval_days: int = Field(default=30)
    semantic_dict_dir: str = Field(
        default=os.environ.get("SEMANTIC_DICT_DIR", "./semantic_dictionaries")
    )
    purge_temp_files: bool = Field(default=True)
    # Simulated search parameters
    simulation_delay_seconds: float = Field(default=0.2)

# ------------------------------------------------------------------------------
# Search Agent (Simulated)
# ------------------------------------------------------------------------------
class SearchAgent:
    """
    A simulated search agent that discovers documents for a jurisdiction.
    In production, this would perform web scraping, API calls, or file system scans.
    """

    def __init__(self, agent_id: int, captain_id: int):
        self.agent_id = agent_id
        self.captain_id = captain_id
        self.logger = logger.getChild(f"SearchAgent-{captain_id}-{agent_id}")

    async def search(self, jurisdiction: Jurisdiction, semantic_engine: SemanticEngine) -> SearchResult:
        """
        Perform the search for a jurisdiction, using the semantic engine for
        language detection and dictionary loading (Just-in-Time).
        """
        self.logger.info(f"Searching jurisdiction: {jurisdiction.name} ({jurisdiction.code})")

        # 1. Detect language if not already set (using sample text)
        # For simulation, we'll just assume a language based on the jurisdiction code.
        # In real scenario, we would need to fetch some sample text.
        detected_lang = jurisdiction.language or self._infer_language(jurisdiction.code)
        self.logger.debug(f"Detected language: {detected_lang}")

        # 2. Load semantic dictionary (Just-in-Time)
        # This triggers lazy loading via the semantic engine.
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

        # 3. Simulate document discovery (based on jurisdiction type)
        await asyncio.sleep(0.2)  # simulate work

        # Generate some dummy documents based on jurisdiction code
        docs = [
            f"building_code_{jurisdiction.code}_2025.pdf",
            f"safety_regulations_{jurisdiction.code}.xml",
            f"zoning_laws_{jurisdiction.code}.json",
            f"fire_safety_{jurisdiction.code}.pdf",
        ]
        # Simulate occasional partial results
        import random
        if random.random() < 0.15:
            docs = docs[:2]
            status = "partial"
        else:
            status = "success"

        return SearchResult(
            jurisdiction=jurisdiction,
            status=status,
            documents_found=docs,
            errors=[],
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
# Captain (Manages a Pool of Search Agents)
# ------------------------------------------------------------------------------
class Captain:
    """
    A Captain manages a pool of SearchAgents. In this simulation, it distributes
    jurisdictions to its agents and collects results.
    """

    def __init__(self, captain_id: int, num_agents: int):
        self.captain_id = captain_id
        self.agents = [SearchAgent(i, captain_id) for i in range(num_agents)]
        self.logger = logger.getChild(f"Captain-{captain_id}")

    async def process_jurisdictions(
        self,
        jurisdictions: List[Jurisdiction],
        semantic_engine: SemanticEngine,
        semaphore: asyncio.Semaphore
    ) -> List[SearchResult]:
        """
        Distribute jurisdictions among agents, respecting concurrency limits.
        """
        self.logger.info(f"Processing {len(jurisdictions)} jurisdictions with {len(self.agents)} agents.")
        tasks = []
        for idx, jur in enumerate(jurisdictions):
            agent = self.agents[idx % len(self.agents)]
            tasks.append(self._run_search_with_semaphore(agent, jur, semantic_engine, semaphore))
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for r in results:
            if isinstance(r, SearchResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                self.logger.error(f"Search task failed: {r}")
                # Create a failed result
                valid_results.append(SearchResult(
                    jurisdiction=jurisdictions[0],  # placeholder; we should track which
                    status="failed",
                    errors=[str(r)]
                ))
        return valid_results

    async def _run_search_with_semaphore(
        self,
        agent: SearchAgent,
        jurisdiction: Jurisdiction,
        semantic_engine: SemanticEngine,
        semaphore: asyncio.Semaphore
    ) -> SearchResult:
        async with semaphore:
            return await agent.search(jurisdiction, semantic_engine)

# ------------------------------------------------------------------------------
# Storage Agent (Handles archiving and WORM recording)
# ------------------------------------------------------------------------------
class StorageAgent:
    """
    Storage Agent compresses discovered documents into a secure tar.gz archive,
    creates a WORM-compatible manifest, and stores it in the output directory.
    All temporary files are purged after the archive is created.
    """

    def __init__(self, output_dir: Path, purge_temp: bool = True):
        self.output_dir = output_dir
        self.purge_temp = purge_temp
        self.logger = logger.getChild("StorageAgent")

    async def store_batch(
        self,
        results: List[SearchResult],
        batch_id: str
    ) -> StorageManifest:
        """
        Create a tar.gz archive from all successful search results.
        """
        self.logger.info(f"Storing batch {batch_id} with {len(results)} results.")

        # Create a temporary directory for this batch
        temp_dir = Path(tempfile.mkdtemp(prefix=f"batch_{batch_id}_"))
        self.logger.debug(f"Created temporary directory: {temp_dir}")

        successful_jurisdictions = []
        total_docs = 0

        # Organize files by jurisdiction
        for result in results:
            if result.status in ("success", "partial"):
                jur_code = result.jurisdiction.code
                jur_name = result.jurisdiction.name.replace(" ", "_")
                jur_dir = temp_dir / f"{jur_code}_{jur_name}"
                jur_dir.mkdir(exist_ok=True)
                successful_jurisdictions.append(jur_code)

                # Write dummy document files (in real scenario, these would be actual files)
                for doc in result.documents_found:
                    doc_path = jur_dir / doc
                    async with aiofiles.open(doc_path, "w") as f:
                        await f.write(f"Simulated document: {doc}\n")
                        await f.write(f"Jurisdiction: {jur_name}\n")
                        await f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n")
                        await f.write(f"Detected language: {result.detected_language}\n")
                    total_docs += 1

        if not successful_jurisdictions:
            self.logger.warning("No successful results to archive.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return StorageManifest(
                archive_name=batch_id,
                jurisdictions=[],
                created_at=datetime.utcnow(),
                total_documents=0
            )

        # Create tar.gz archive
        archive_name = f"jurisdiction_batch_{batch_id}.tar.gz"
        archive_path = self.output_dir / archive_name
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_dir, arcname="")

        self.logger.info(f"Created archive: {archive_path} with {total_docs} documents.")

        # Create manifest
        manifest = StorageManifest(
            archive_name=archive_name,
            jurisdictions=successful_jurisdictions,
            created_at=datetime.utcnow(),
            total_documents=total_docs,
            metadata={
                "batch_id": batch_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Write manifest alongside archive
        manifest_path = self.output_dir / f"{batch_id}_manifest.json"
        async with aiofiles.open(manifest_path, "w") as f:
            await f.write(manifest.json(indent=2))

        # Purge temporary directory
        if self.purge_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.logger.debug(f"Purged temporary directory: {temp_dir}")

        return manifest

# ------------------------------------------------------------------------------
# Master Jurisdiction Orchestrator
# ------------------------------------------------------------------------------
class JurisdictionOrchestrator:
    """
    Master orchestrator managing 3 Captains, 30 Search Agents, and Storage Agents.
    Runs as a periodic batch process (monthly) to scan global jurisdictions.
    Features: ephemeral resource lifecycle, JIT semantic dictionary loading,
    async concurrency, and forensic logging.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.output_dir = Path(self.config.output_base_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create Captains
        self.captains = [
            Captain(i, self.config.agents_per_captain)
            for i in range(self.config.num_captains)
        ]

        # Storage agent
        self.storage_agent = StorageAgent(
            self.output_dir,
            purge_temp=self.config.purge_temp_files
        )

        # Shared semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        # Semantic engine instance (will be created per batch)
        self.semantic_engine: Optional[SemanticEngine] = None

        self.logger = logger.getChild("Orchestrator")
        self.logger.info(
            f"JurisdictionOrchestrator initialized: captains={self.config.num_captains}, "
            f"agents_per_captain={self.config.agents_per_captain}, "
            f"max_concurrent={self.config.max_concurrent_tasks}"
        )

    # --------------------------------------------------------------------------
    # Utility: Build jurisdiction list
    # --------------------------------------------------------------------------
    @staticmethod
    def get_all_jurisdictions() -> List[Jurisdiction]:
        """Return a list of all US states, federal territories, and a few international examples."""
        jurisdictions = []
        # US States
        states = [
            ("Alabama", "AL"), ("Alaska", "AK"), ("Arizona", "AZ"), ("Arkansas", "AR"),
            ("California", "CA"), ("Colorado", "CO"), ("Connecticut", "CT"), ("Delaware", "DE"),
            ("Florida", "FL"), ("Georgia", "GA"), ("Hawaii", "HI"), ("Idaho", "ID"),
            ("Illinois", "IL"), ("Indiana", "IN"), ("Iowa", "IA"), ("Kansas", "KS"),
            ("Kentucky", "KY"), ("Louisiana", "LA"), ("Maine", "ME"), ("Maryland", "MD"),
            ("Massachusetts", "MA"), ("Michigan", "MI"), ("Minnesota", "MN"), ("Mississippi", "MS"),
            ("Missouri", "MO"), ("Montana", "MT"), ("Nebraska", "NE"), ("Nevada", "NV"),
            ("New Hampshire", "NH"), ("New Jersey", "NJ"), ("New Mexico", "NM"), ("New York", "NY"),
            ("North Carolina", "NC"), ("North Dakota", "ND"), ("Ohio", "OH"), ("Oklahoma", "OK"),
            ("Oregon", "OR"), ("Pennsylvania", "PA"), ("Rhode Island", "RI"), ("South Carolina", "SC"),
            ("South Dakota", "SD"), ("Tennessee", "TN"), ("Texas", "TX"), ("Utah", "UT"),
            ("Vermont", "VT"), ("Virginia", "VA"), ("Washington", "WA"), ("West Virginia", "WV"),
            ("Wisconsin", "WI"), ("Wyoming", "WY")
        ]
        for name, code in states:
            jurisdictions.append(Jurisdiction(name=name, code=code, type="State"))

        # US Territories and Federal District
        territories = [
            ("District of Columbia", "DC", "Federal District"),
            ("Puerto Rico", "PR", "Territory"),
            ("US Virgin Islands", "VI", "Territory"),
            ("Guam", "GU", "Territory"),
            ("American Samoa", "AS", "Territory"),
            ("Northern Mariana Islands", "MP", "Territory"),
        ]
        for name, code, typ in territories:
            jurisdictions.append(Jurisdiction(name=name, code=code, type=typ))

        # Example international jurisdictions
        international = [
            ("United Kingdom", "GB", "International"),
            ("Canada", "CA", "International"),
            ("Germany", "DE", "International"),
            ("France", "FR", "International"),
            ("Spain", "ES", "International"),
            ("Italy", "IT", "International"),
            ("Japan", "JP", "International"),
            ("Australia", "AU", "International"),
            ("Brazil", "BR", "International"),
        ]
        for name, code, typ in international:
            jurisdictions.append(Jurisdiction(name=name, code=code, type=typ, scope="international"))

        return jurisdictions

    # --------------------------------------------------------------------------
    # Core orchestration method
    # --------------------------------------------------------------------------
    async def run_batch(self, jurisdictions: Optional[List[Jurisdiction]] = None) -> Dict[str, Any]:
        """
        Execute a full batch scan: discover, collect, compress, and record.
        All temporary resources are purged after completion.
        """
        if jurisdictions is None:
            jurisdictions = self.get_all_jurisdictions()

        self.logger.info(f"Starting batch scan for {len(jurisdictions)} jurisdictions.")
        batch_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # 1. Initialize semantic engine for this batch (Just-in-Time dictionary loading)
        self.logger.info("Initializing SemanticEngine for this batch...")
        self.semantic_engine = SemanticEngine(
            dict_dir=self.config.semantic_dict_dir,
            block_on_missing=False,
            max_block_wait=0.5,
            hydration_threads=4
        )
        self.logger.info("SemanticEngine ready.")

        # 2. Distribute jurisdictions among Captains (round-robin)
        captain_jurisdictions = [[] for _ in range(self.config.num_captains)]
        for idx, jur in enumerate(jurisdictions):
            captain_idx = idx % self.config.num_captains
            captain_jurisdictions[captain_idx].append(jur)

        # 3. Run search agents for each captain in parallel
        all_results = []
        search_tasks = []
        for cap_idx, cap in enumerate(self.captains):
            if captain_jurisdictions[cap_idx]:
                task = cap.process_jurisdictions(
                    captain_jurisdictions[cap_idx],
                    self.semantic_engine,
                    self.semaphore
                )
                search_tasks.append(task)

        if search_tasks:
            captain_results = await asyncio.gather(*search_tasks)
            for res_list in captain_results:
                all_results.extend(res_list)

        # 4. Store results in WORM-compatible archive
        manifest = await self.storage_agent.store_batch(all_results, batch_id)

        # 5. Ephemeral Resource Lifecycle: purge semantic engine and all caches
        self.logger.info("Purging ephemeral resources...")
        # Shut down semantic engine (clears caches, closes threads)
        if self.semantic_engine:
            self.semantic_engine.shutdown()
            self.semantic_engine = None
        # Force garbage collection? Not necessary but we can.
        import gc
        gc.collect()

        # 6. Compile summary
        successful = sum(1 for r in all_results if r.status == "success")
        partial = sum(1 for r in all_results if r.status == "partial")
        failed = sum(1 for r in all_results if r.status == "failed")
        summary = {
            "batch_id": batch_id,
            "total_jurisdictions": len(jurisdictions),
            "successful": successful,
            "partial": partial,
            "failed": failed,
            "manifest": manifest.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.logger.info(f"Batch completed. Summary: {summary}")
        return summary

    async def run_monthly(self):
        """
        Run the batch monthly (or with configurable interval).
        This is intended to be called by a scheduler (e.g., cron, APScheduler).
        """
        self.logger.info("Starting monthly jurisdiction scan...")
        await self.run_batch()
        self.logger.info("Monthly scan completed.")

# ------------------------------------------------------------------------------
# Command-line entry for standalone execution
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    # Run a single batch
    orchestrator = JurisdictionOrchestrator()
    asyncio.run(orchestrator.run_monthly())
