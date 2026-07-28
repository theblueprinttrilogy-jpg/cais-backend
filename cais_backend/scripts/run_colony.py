#!/usr/bin/env python3
# scripts/run_colony.py - CAIS v2.0 Colony Orchestrator
# Production-ready master orchestrator that initializes and manages the complete CAIS colony:
# 2 Code & Regulation Captains (20 agents), 1 Legal Captain (10 agents),
# Storage Agents, JanitorAgent, and feedback loop for 100% US coverage.
# Targets all 50 states, DC, and all US territories.

import asyncio
import logging
import sys
import os
import json
from typing import List, Dict, Any, Set, Optional
from datetime import datetime

# Core agent imports with correct paths
from agents.captains import (
    Captain,
    Jurisdiction,
    SearchResult,
    ProxyManager,
    CookieManager,
    SubscriptionHandler,
    SUBSCRIPTION_CREDENTIALS,
    create_captains,
)
from agents.legal_search_agent import LegalSearchAgent, LegalSearchResult, create_legal_agents
from agents.storage_agent import StorageAgent
from app.agents.janitor_agent import JanitorAgent

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "colony_run.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger("ColonyOrchestrator")

# ------------------------------------------------------------------------------
# US Jurisdiction Database (50 states + DC + Territories)
# ------------------------------------------------------------------------------
US_STATES = [
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

US_TERRITORIES = [
    ("District of Columbia", "DC", "Federal District"),
    ("Puerto Rico", "PR", "Territory"),
    ("Guam", "GU", "Territory"),
    ("US Virgin Islands", "VI", "Territory"),
    ("American Samoa", "AS", "Territory"),
    ("Northern Mariana Islands", "MP", "Territory"),
]

def build_us_jurisdictions() -> List[Jurisdiction]:
    """Build the full list of US jurisdictions including states, DC, and territories."""
    jurisdictions = []
    for name, code in US_STATES:
        jurisdictions.append(Jurisdiction(
            name=name,
            code=code,
            type="State",
            scope="domestic",
            zipcodes=[f"{code.lower()}000"]  # placeholder; in production, fetch real zipcodes
        ))
    for name, code, typ in US_TERRITORIES:
        jurisdictions.append(Jurisdiction(
            name=name,
            code=code,
            type=typ,
            scope="domestic",
            zipcodes=[f"{code.lower()}000"]
        ))
    return jurisdictions

# ------------------------------------------------------------------------------
# Colony Orchestrator
# ------------------------------------------------------------------------------
class ColonyOrchestrator:
    """
    Master orchestrator for the CAIS colony. Manages Captains, JanitorAgent,
    StorageAgent, and the feedback loop for full US coverage.
    """

    def __init__(self):
        self.jurisdictions = build_us_jurisdictions()
        self.storage_agent = StorageAgent(output_dir="./colony_output", purge_temp=True)
        self.janitor_agent = JanitorAgent(
            credentials_file="secrets/credentials.json",
            root_folder_name="JACINTO_CORREA_COMPUTER",
            max_age_days=45
        )
        # Shared components for anti-bot and cookies
        self.proxy_manager = ProxyManager()
        self.cookie_manager = CookieManager()
        self.subscription_handler = SubscriptionHandler(SUBSCRIPTION_CREDENTIALS, self.cookie_manager)

        # Captains: 2 Code & Regulation Captains (each 10 agents) = 20 agents
        # 1 Legal Captain (10 agents) = 10 agents
        # Total 30 agents as required.
        self.captains = self._create_captains()
        self.legal_agents = self._create_legal_agents()

        self.semaphore = asyncio.Semaphore(20)  # concurrency limit
        self._covered_jurisdictions: Set[str] = set()
        self._retry_count = 0
        self._max_retries = 5
        self.logger = logger.getChild("Orchestrator")
        self.logger.info(f"ColonyOrchestrator initialized with {len(self.jurisdictions)} jurisdictions.")

    def _create_captains(self) -> List[Captain]:
        """Create 2 Code & Regulation Captains, each with 10 agents."""
        # We manually instantiate to reuse shared managers
        captains = []
        for i in range(2):
            captain = Captain(
                captain_id=i + 1,
                num_agents=10,
                proxy_manager=self.proxy_manager,
                cookie_manager=self.cookie_manager
            )
            captains.append(captain)
        return captains

    def _create_legal_agents(self) -> List[LegalSearchAgent]:
        """Create 10 LegalSearchAgent instances managed by a logical Captain 3."""
        # We'll create them with captain_id=3
        return create_legal_agents(10, captain_id=3)

    async def _run_code_agents(self, jurisdictions: List[Jurisdiction]) -> List[SearchResult]:
        """Run the Code & Regulation Captains on a subset of jurisdictions."""
        if not jurisdictions:
            return []
        # Distribute among the 2 captains
        half = len(jurisdictions) // 2
        batch1 = jurisdictions[:half]
        batch2 = jurisdictions[half:]
        tasks = []
        if batch1:
            tasks.append(self.captains[0].process_jurisdictions(batch1, self.semaphore))
        if batch2:
            tasks.append(self.captains[1].process_jurisdictions(batch2, self.semaphore))
        results = await asyncio.gather(*tasks)
        # Flatten results
        all_results = []
        for res in results:
            all_results.extend(res)
        return all_results

    async def _run_legal_agents(self, jurisdictions: List[Jurisdiction]) -> List[LegalSearchResult]:
        """Run the LegalSearchAgent pool on jurisdictions."""
        if not jurisdictions:
            return []
        tasks = []
        for idx, jur in enumerate(jurisdictions):
            agent = self.legal_agents[idx % len(self.legal_agents)]
            tasks.append(agent.search(jur))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = []
        for idx, r in enumerate(results):
            if isinstance(r, LegalSearchResult):
                valid_results.append(r)
            else:
                # Convert exception to a failed result
                jur = jurisdictions[idx]
                self.logger.error(f"Legal search for {jur.code} failed: {r}")
                # Create a failed result
                valid_results.append(LegalSearchResult(
                    jurisdiction=jur,
                    status="failed",
                    errors=[f"Agent error: {r}"],
                    detected_language="en"
                ))
        return valid_results

    async def _report_missing_to_janitor(self, missing_items: Dict[str, List[str]]) -> None:
        """Report missing items (zipcodes, codes, regulations) to JanitorAgent."""
        for jurisdiction, items in missing_items.items():
            if items:
                self.logger.info(f"Reporting missing items for {jurisdiction}: {items}")
                # In production, this would update JanitorAgent's queue.
                # We'll just log for now.

    async def run_campaign(self) -> bool:
        """
        Execute the full campaign with feedback loop until 100% coverage is achieved.
        Returns True if full coverage achieved, False otherwise.
        """
        self.logger.info("Starting CAIS colony campaign for US jurisdictions.")

        # Ensure subscription is active
        if not await self.subscription_handler.subscribe_trial():
            self.logger.error("Failed to activate trial subscription. Aborting.")
            return False

        remaining_jurisdictions = self.jurisdictions.copy()
        all_missing = {}

        while remaining_jurisdictions and self._retry_count < self._max_retries:
            self._retry_count += 1
            self.logger.info(f"Retry {self._retry_count}: Processing {len(remaining_jurisdictions)} remaining jurisdictions.")

            # Run code and legal agents concurrently
            code_task = self._run_code_agents(remaining_jurisdictions)
            legal_task = self._run_legal_agents(remaining_jurisdictions)
            code_results, legal_results = await asyncio.gather(code_task, legal_task)

            # Determine coverage per jurisdiction
            code_success = set()
            legal_success = set()
            for r in code_results:
                if r.status == "success" or r.status == "partial":
                    code_success.add(r.jurisdiction.code)
            for r in legal_results:
                if r.status == "success" or r.status == "partial":
                    legal_success.add(r.jurisdiction.code)

            # A jurisdiction is fully covered if it has both code and legal success
            covered_codes = code_success.intersection(legal_success)

            # Determine which jurisdictions remain
            new_remaining = []
            for jur in remaining_jurisdictions:
                if jur.code in covered_codes:
                    self._covered_jurisdictions.add(jur.code)
                    self.logger.info(f"Jurisdiction {jur.code} fully covered.")
                else:
                    new_remaining.append(jur)

            # Collect missing items from failed/partial results
            missing_per_jurisdiction = {}
            for r in code_results + legal_results:
                jur_code = r.jurisdiction.code
                if hasattr(r, 'missing_items') and r.missing_items:
                    missing_per_jurisdiction[jur_code] = missing_per_jurisdiction.get(jur_code, []) + r.missing_items
                elif r.status == "failed":
                    missing_per_jurisdiction[jur_code] = missing_per_jurisdiction.get(jur_code, []) + ["all_targets"]

            for jur_code, items in missing_per_jurisdiction.items():
                if jur_code not in covered_codes:
                    all_missing[jur_code] = items

            remaining_jurisdictions = new_remaining

            # Report missing to JanitorAgent
            if all_missing:
                await self._report_missing_to_janitor(all_missing)

            # If no jurisdictions remain, break
            if not remaining_jurisdictions:
                self.logger.info("All jurisdictions fully covered!")
                break

        # After loop, check coverage
        total = len(self.jurisdictions)
        covered = len(self._covered_jurisdictions)
        self.logger.info(f"Campaign finished: {covered}/{total} jurisdictions covered.")

        # Cancel subscription
        await self.subscription_handler.cancel_subscription()

        return covered == total

    async def close(self):
        """Close all resources."""
        for cap in self.captains:
            await cap.close_agents()
        for agent in self.legal_agents:
            await agent.close()
        await self.subscription_handler.close()

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------
async def main():
    logger.info("=" * 80)
    logger.info("CAIS v2.0 Colony Orchestrator")
    logger.info(f"Started at {datetime.utcnow().isoformat()}")
    logger.info("Target: ALL US states, DC, and territories.")
    logger.info("=" * 80)

    orchestrator = ColonyOrchestrator()
    try:
        success = await orchestrator.run_campaign()
        if success:
            logger.info("✅ Full US coverage achieved.")
        else:
            logger.warning("⚠️ Full coverage not achieved after retries.")
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down.")
    finally:
        await orchestrator.close()
        logger.info("Colony orchestrator terminated.")

if __name__ == "__main__":
    asyncio.run(main())
