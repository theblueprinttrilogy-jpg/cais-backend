"""
GlobalJurisdictionAgent for CAIS backend.

This agent synchronises with the Three Captains Orchestrator, ingests global
postal codes and jurisdictional data (from Wikipedia or open datasets),
and performs a gap analysis to identify missing regulatory documents in
the Google Drive repository.

It then triggers the appropriate search agents to fetch missing codes.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup

from app.services.drive_sync_service import DriveSyncService
from app.services.zip_code_service import ZipCodeService
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class JurisdictionCoverage:
    """Represents the coverage status of a jurisdiction."""
    country: str
    state: Optional[str]
    county: Optional[str]
    municipality: Optional[str]
    has_federal: bool = False
    has_state: bool = False
    has_county: bool = False
    has_municipal: bool = False
    missing_levels: List[str] = field(default_factory=list)

    def is_fully_covered(self) -> bool:
        """Check if all applicable levels are covered."""
        all_levels = []
        if self.state is not None:
            all_levels.append("state")
        if self.county is not None:
            all_levels.append("county")
        if self.municipality is not None:
            all_levels.append("municipal")
        # Federal is always required
        all_levels.append("federal")
        for level in all_levels:
            if level == "federal" and not self.has_federal:
                return False
            if level == "state" and not self.has_state:
                return False
            if level == "county" and not self.has_county:
                return False
            if level == "municipal" and not self.has_municipal:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "country": self.country,
            "state": self.state,
            "county": self.county,
            "municipality": self.municipality,
            "has_federal": self.has_federal,
            "has_state": self.has_state,
            "has_county": self.has_county,
            "has_municipal": self.has_municipal,
            "missing_levels": self.missing_levels,
            "fully_covered": self.is_fully_covered()
        }


class GlobalJurisdictionAgent:
    """
    Agent responsible for global jurisdiction discovery and gap analysis.

    It interacts with the DriveSyncService to understand what regulatory
    documents are already present, and uses the ZipCodeService to map
    postal codes to jurisdictions. It also communicates with the
    Three Captains Orchestrator (via Redis or direct queue) to trigger
    acquisition of missing codes.
    """

    # Comprehensive fallback list of all US states, DC, and major territories.
    # This guarantees 100% reliability and avoids any pycountry issues.
    US_JURISDICTIONS = [
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
        "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
        "New Hampshire", "New Jersey", "New Mexico", "New York",
        "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
        "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
        "West Virginia", "Wisconsin", "Wyoming",
        "District of Columbia",  # Washington D.C.
        "Puerto Rico", "Guam", "U.S. Virgin Islands",
        "American Samoa", "Northern Mariana Islands"
    ]

    def __init__(
        self,
        drive_service: DriveSyncService,
        zip_code_service: ZipCodeService,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialise the GlobalJurisdictionAgent.

        Args:
            drive_service: Instance of DriveSyncService for Drive operations.
            zip_code_service: Instance of ZipCodeService for jurisdiction mapping.
            redis_client: Optional Redis client for orchestration messaging.
        """
        self.drive_service = drive_service
        self.zip_service = zip_code_service
        self.redis = redis_client
        self._coverage_cache: Dict[tuple, JurisdictionCoverage] = {}
        self._cache_ttl = 3600  # seconds

    async def _fetch_usa_and_territories_jurisdictions(self) -> List[Dict[str, str]]:
        """
        Fetch a comprehensive list of jurisdictions for the United States,
        including all 50 states, Washington D.C., and major US territories.

        This method uses a hardcoded fallback list to guarantee reliability,
        without relying on pycountry.subdivisions which can cause KeyError.

        Returns:
            List of dicts with keys: country ("United States"), state (full name),
            county (None), city (None) for each state/territory.
        """
        jurisdictions = []
        for state_name in self.US_JURISDICTIONS:
            jurisdictions.append({
                "country": "United States",
                "state": state_name,
                "county": None,
                "city": None,
            })
        logger.info("Returning %d US jurisdictions from fallback list.", len(jurisdictions))
        return jurisdictions

    async def _fetch_global_jurisdictions(self) -> List[Dict[str, str]]:
        """
        Fetch the target jurisdictions for gap analysis. For CAIS, we focus
        exclusively on the United States and its territories.

        Returns:
            List of dicts with keys: country ("United States"), state (full name),
            county (None), city (None) for each state/territory.
        """
        return await self._fetch_usa_and_territories_jurisdictions()

    async def _parse_wikipedia_postal_codes(self, country: str) -> List[Dict[str, str]]:
        """
        Parse the Wikipedia page for postal codes in a given country.

        Args:
            country: Country name.

        Returns:
            List of dicts with 'city', 'county', 'state' if available.
        """
        # This is a stub for a more complex parser.
        # In production, use BeautifulSoup to extract tables.
        # For now, return empty.
        return []

    async def _fetch_jurisdictions_from_orchestrator(self) -> List[Dict[str, str]]:
        """
        Fetch the target jurisdiction list from the orchestrator's queue (e.g., Redis).

        Returns:
            List of jurisdiction dicts.
        """
        if not self.redis:
            logger.warning("Redis client not set, cannot fetch orchestrator list.")
            return []
        # Placeholder: read from Redis key
        # data = await self.redis.lrange("cais:jurisdictions:queue", 0, -1)
        # return [json.loads(item) for item in data]
        return []

    async def _get_existing_coverage(self) -> Dict[tuple, JurisdictionCoverage]:
        """
        Retrieve coverage information from the Drive repository using
        ZipCodeService.

        Returns:
            Dict mapping (city, county, state) to JurisdictionCoverage.
        """
        # Use ZipCodeService to discover jurisdictions that have some files.
        discovered = await self.zip_service.discover_jurisdictions()
        coverage_map = {}
        for entry in discovered:
            city = entry.get("city", "Unknown")
            county = entry.get("county", "Unknown")
            state = entry.get("state", "Unknown")
            # Get coverage levels
            coverage = await self.zip_service.get_coverage_status(entry)
            # Convert coverage dict to JurisdictionCoverage
            cov = JurisdictionCoverage(
                country="United States",
                state=state if state != "Unknown" else None,
                county=county if county != "Unknown" else None,
                municipality=city if city != "Unknown" else None,
                has_federal=coverage.get("federal", False),
                has_state=coverage.get("state", False),
                has_county=coverage.get("county", False),
                has_municipal=coverage.get("municipal", False),
            )
            # Compute missing levels
            missing = []
            if not cov.has_federal:
                missing.append("federal")
            if cov.state and not cov.has_state:
                missing.append("state")
            if cov.county and not cov.has_county:
                missing.append("county")
            if cov.municipality and not cov.has_municipal:
                missing.append("municipal")
            cov.missing_levels = missing
            coverage_map[(city, county, state)] = cov
        return coverage_map

    async def analyze_coverage(self, target_jurisdictions: Optional[List[Dict[str, str]]] = None) -> List[JurisdictionCoverage]:
        """
        Perform gap analysis: compare target jurisdictions (from orchestrator or global list)
        against existing coverage in Drive.

        Args:
            target_jurisdictions: List of dicts with 'country', 'state', 'county', 'city'.
                                  If None, fetches from orchestrator or falls back to global list.

        Returns:
            List of JurisdictionCoverage objects with missing levels filled.
        """
        if target_jurisdictions is None:
            # Try orchestrator first
            target_jurisdictions = await self._fetch_jurisdictions_from_orchestrator()
            if not target_jurisdictions:
                # Fallback to global list (US states and territories)
                target_jurisdictions = await self._fetch_global_jurisdictions()
                if not target_jurisdictions:
                    logger.error("No target jurisdictions available for analysis.")
                    return []

        # Get existing coverage from Drive
        existing_coverage = await self._get_existing_coverage()

        results = []
        for jur in target_jurisdictions:
            city = jur.get("city", "Unknown")
            county = jur.get("county", "Unknown")
            state = jur.get("state", "Unknown")
            country = jur.get("country", "United States")

            # Check if this jurisdiction exists in coverage map
            key = (city, county, state)
            if key in existing_coverage:
                cov = existing_coverage[key]
                # Ensure country matches
                cov.country = country
                results.append(cov)
            else:
                # No coverage at all for this jurisdiction
                cov = JurisdictionCoverage(
                    country=country,
                    state=state if state != "Unknown" else None,
                    county=county if county != "Unknown" else None,
                    municipality=city if city != "Unknown" else None,
                    has_federal=False,
                    has_state=False,
                    has_county=False,
                    has_municipal=False,
                    missing_levels=[]
                )
                # Determine which levels are applicable
                missing = ["federal"]
                if state and state != "Unknown":
                    missing.append("state")
                if county and county != "Unknown":
                    missing.append("county")
                if city and city != "Unknown":
                    missing.append("municipal")
                cov.missing_levels = missing
                results.append(cov)

        return results

    async def trigger_search_agents(self, gaps: List[JurisdictionCoverage]) -> None:
        """
        For each jurisdiction with missing levels, push tasks to the orchestrator
        or directly to search agents to fetch the missing regulatory documents.

        Args:
            gaps: List of JurisdictionCoverage objects where missing_levels is not empty.
        """
        if not gaps:
            logger.info("No gaps to fill.")
            return

        # For each gap, construct a task message
        for gap in gaps:
            if not gap.missing_levels:
                continue
            # Determine which search agent to trigger based on missing levels.
            # For simplicity, we'll push a generic task to a Redis queue.
            task = {
                "country": gap.country,
                "state": gap.state,
                "county": gap.county,
                "municipality": gap.municipality,
                "missing_levels": gap.missing_levels,
                "timestamp": datetime.utcnow().isoformat()
            }
            if self.redis:
                # Push to a queue that the search agents consume
                await self.redis.rpush("cais:search:queue", json.dumps(task))
                logger.info("Pushed task for %s to search queue.", task)
            else:
                # Directly invoke search agent (stub)
                logger.warning("Redis not configured; would trigger search for: %s", task)

    async def run_sync_cycle(self) -> Dict[str, Any]:
        """
        Perform a full synchronization cycle:
        1. Fetch target jurisdictions (from orchestrator or global list).
        2. Analyze coverage against Drive.
        3. Trigger search agents for missing documents.
        4. Return a report.

        Returns:
            Dict with report statistics.
        """
        logger.info("Starting global jurisdiction sync cycle.")
        target_jurisdictions = await self._fetch_jurisdictions_from_orchestrator()
        if not target_jurisdictions:
            target_jurisdictions = await self._fetch_global_jurisdictions()
            logger.info("No orchestrator list; using global list with %d entries.", len(target_jurisdictions))

        coverage_results = await self.analyze_coverage(target_jurisdictions)
        gaps = [c for c in coverage_results if not c.is_fully_covered()]

        await self.trigger_search_agents(gaps)

        report = {
            "total_jurisdictions": len(coverage_results),
            "fully_covered": sum(1 for c in coverage_results if c.is_fully_covered()),
            "partial_or_missing": len(gaps),
            "gaps": [g.to_dict() for g in gaps[:10]],  # limit for brevity
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info("Sync cycle completed. Report: %s", report)
        return report


# For testing / standalone execution
async def main():
    """Example usage of the GlobalJurisdictionAgent."""
    # Setup dependencies
    drive_service = DriveSyncService()
    zip_service = ZipCodeService(drive_service)

    # Optionally, set Redis client (mock or real)
    redis_client = None  # In production, use aioredis or similar

    agent = GlobalJurisdictionAgent(drive_service, zip_service, redis_client)
    report = await agent.run_sync_cycle()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
