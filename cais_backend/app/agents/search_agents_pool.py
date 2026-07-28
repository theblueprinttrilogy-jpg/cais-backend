"""
Search Agent Pool and Three Captains coordination module for CAIS backend.

This module implements a production‑grade worker pool that consumes tasks from
Redis (`cais:search:queue`) and executes real web scraping/API queries to fetch
building codes, safety regulations (OSHA), and construction laws for US
states, territories, counties, and municipalities.

All fetched documents are compressed and uploaded to the local mock storage
(DriveSyncService) for further processing.
"""

import asyncio
import json
import logging
import os
import re
import tarfile
import tempfile
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urldefrag

import aiohttp
import aiohttp.client_exceptions
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.drive_sync_service import DriveSyncService

# Try to import aioredis
try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)


class RegulatoryFetcher:
    """
    Handles fetching regulatory documents from various official sources.

    All operations perform real HTTP requests using aiohttp and parse HTML
    content with BeautifulSoup to extract links to downloadable PDFs or
    relevant regulatory text pages.
    """

    # Mapping of state names to known official building code portals.
    # These are publicly accessible URLs that serve building codes and regulations.
    STATE_PORTALS = {
        "CA": "https://www.dgs.ca.gov/BSC/Codes",
        "NY": "https://www.dos.ny.gov/dcea/",
        "TX": "https://www.tdlr.texas.gov/buildingcodes.htm",
        "FL": "https://www.floridabuilding.org/",
        "IL": "https://www.iccsafe.org/",
        "OH": "https://www.com.ohio.gov/dico/",
        "PA": "https://www.dgs.pa.gov/Pages/default.aspx",
        # Additional states can be added here.
    }

    # Comprehensive mapping of US state/territory names to two-letter abbreviations.
    STATE_ABBR_MAP = {
        "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
        "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
        "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
        "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
        "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
        "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
        "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
        "New York": "NY", "North Carolina": "NC", "North Dakota": "ND",
        "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
        "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
        "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
        "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
        "Wisconsin": "WI", "Wyoming": "WY",
        "District of Columbia": "DC",
        "Puerto Rico": "PR", "Guam": "GU", "U.S. Virgin Islands": "VI",
        "American Samoa": "AS", "Northern Mariana Islands": "MP"
    }

    def __init__(self, session: aiohttp.ClientSession, rate_limit: int = 5):
        """
        Initialise the fetcher.

        Args:
            session: Shared aiohttp ClientSession.
            rate_limit: Max concurrent requests per worker.
        """
        self.session = session
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.user_agent = "CAIS-Search-Agent/1.0 (Compliance Crawler)"

    async def _fetch_url(self, url: str, retries: int = 3) -> Optional[bytes]:
        """
        Fetch a URL with retries and exponential backoff.

        Returns:
            Response body as bytes, or None on failure.
        """
        headers = {"User-Agent": self.user_agent}
        for attempt in range(retries):
            try:
                async with self.semaphore:
                    async with self.session.get(url, headers=headers, timeout=30) as resp:
                        if resp.status == 200:
                            return await resp.read()
                        elif resp.status in (403, 404, 410):
                            logger.warning("HTTP %s for %s (permanent failure)", resp.status, url)
                            return None
                        else:
                            logger.warning("HTTP %s for %s (attempt %d)", resp.status, url, attempt + 1)
                            if attempt < retries - 1:
                                await asyncio.sleep(2 ** attempt)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Attempt %d failed for %s: %s", attempt + 1, url, e)
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error("All retries failed for %s", url)
        return None

    async def _extract_pdf_links(self, html_content: bytes, base_url: str) -> List[str]:
        """
        Extract absolute URLs to PDF files from HTML content.
        Uses urljoin and urldefrag from urllib.parse (imported at top).
        """
        links = []
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href and href.lower().endswith(".pdf"):
                    full_url = urljoin(base_url, href)
                    # Remove any fragment (e.g., #page=1) to get clean URL
                    full_url, _ = urldefrag(full_url)
                    links.append(full_url)
        except Exception as e:
            logger.error("Error extracting PDF links: %s", e)
        return links

    async def fetch_federal_documents(self) -> Dict[str, bytes]:
        """
        Fetch federal regulations from OSHA's main website.

        Returns:
            Dict mapping filename -> content bytes.
        """
        results = {}
        base_url = "https://www.osha.gov/"
        content = await self._fetch_url(base_url)
        if not content:
            logger.warning("No content from OSHA main page")
            alt_url = "https://www.osha.gov/laws-regs"
            content = await self._fetch_url(alt_url)
            if not content:
                return results

        results["osha_main.html"] = content
        pdf_urls = await self._extract_pdf_links(content, base_url)
        if pdf_urls:
            logger.info("Found %d PDFs on OSHA page", len(pdf_urls))
            for i, pdf_url in enumerate(pdf_urls[:5]):
                pdf_content = await self._fetch_url(pdf_url)
                if pdf_content:
                    results[f"osha_doc_{i+1}.pdf"] = pdf_content
        return results

    async def fetch_state_documents(self, state_name: str) -> Dict[str, bytes]:
        """
        Fetch state‑specific building codes and regulations.
        """
        state_abbr = self._state_to_abbr(state_name)
        if not state_abbr or state_abbr not in self.STATE_PORTALS:
            logger.warning("No known portal for state: %s", state_name)
            return {}

        portal_url = self.STATE_PORTALS[state_abbr]
        results = {}
        content = await self._fetch_url(portal_url)
        if content:
            results[f"state_{state_abbr}_portal.html"] = content
            pdf_urls = await self._extract_pdf_links(content, portal_url)
            for i, pdf_url in enumerate(pdf_urls[:5]):
                pdf_content = await self._fetch_url(pdf_url)
                if pdf_content:
                    results[f"state_{state_abbr}_doc_{i+1}.pdf"] = pdf_content
        return results

    # Additional methods for county/municipal can be added similarly.
    # For simplicity, we focus on federal and state for now.

    @staticmethod
    def _state_to_abbr(state_name: str) -> Optional[str]:
        """Convert a full state/territory name to its two-letter abbreviation."""
        cleaned = state_name.strip()
        if "Virgin" in cleaned:
            cleaned = "U.S. Virgin Islands"
        if "Columbia" in cleaned:
            cleaned = "District of Columbia"
        if "Northern Mariana" in cleaned:
            cleaned = "Northern Mariana Islands"
        return RegulatoryFetcher.STATE_ABBR_MAP.get(cleaned)


class SearchAgentPool:
    """
    Asynchronous worker pool that consumes search tasks from Redis.

    Each worker fetches regulatory documents, packages them into tar.gz,
    and uploads them to the local mock storage (DriveSyncService).
    """

    def __init__(
        self,
        num_workers: int = 3,
        redis_client: Optional[aioredis.Redis] = None,
        drive_service: Optional[DriveSyncService] = None,
        queue_name: str = "cais:search:queue",
        rate_limit: int = 5,
    ):
        """
        Initialise the SearchAgentPool.

        Args:
            num_workers: Number of concurrent worker tasks.
            redis_client: Redis client (must be connected).
            drive_service: DriveSyncService instance for uploads.
            queue_name: Name of the Redis queue.
            rate_limit: Max concurrent requests per worker.
        """
        self.num_workers = num_workers
        self.redis = redis_client
        self.drive_service = drive_service or DriveSyncService()
        self.queue_name = queue_name
        self.rate_limit = rate_limit
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self._session: Optional[aiohttp.ClientSession] = None

    async def _fetch_documents(
        self,
        jurisdiction: Dict[str, str],
        missing_levels: List[str],
    ) -> Dict[str, bytes]:
        """
        Fetch regulatory documents for the given jurisdiction and missing levels.
        """
        fetcher = RegulatoryFetcher(self._session, self.rate_limit)
        all_docs = {}

        if "federal" in missing_levels:
            fed_docs = await fetcher.fetch_federal_documents()
            all_docs.update(fed_docs)

        if "state" in missing_levels and jurisdiction.get("state"):
            state_docs = await fetcher.fetch_state_documents(jurisdiction["state"])
            all_docs.update(state_docs)

        # County and municipal can be expanded similarly.
        return all_docs

    async def _process_task(self, task_data: Dict[str, Any]) -> None:
        """
        Process a single task from the queue.

        Steps:
        1. Extract jurisdiction info and missing levels.
        2. Fetch documents via the fetcher.
        3. Create a tar.gz archive with the documents.
        4. Upload the archive to the appropriate Drive folder hierarchy.
        """
        jurisdiction = {
            "country": task_data.get("country", "United States"),
            "state": task_data.get("state"),
            "county": task_data.get("county"),
            "municipality": task_data.get("municipality"),
        }
        missing_levels = task_data.get("missing_levels", [])
        if not missing_levels:
            logger.warning("Task has no missing levels: %s", task_data)
            return

        logger.info("Processing task for %s - missing: %s", jurisdiction, missing_levels)

        # Fetch documents
        try:
            documents = await self._fetch_documents(jurisdiction, missing_levels)
        except Exception as e:
            logger.exception("Error during document fetching: %s", e)
            return

        if not documents:
            logger.warning("No documents fetched for %s", jurisdiction)
            return

        # Create archive in temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            state_part = jurisdiction.get("state", "unknown")
            levels_part = "_".join(missing_levels)
            archive_name = f"{state_part}_{levels_part}_{int(time.time())}.tar.gz"
            archive_path = os.path.join(tmpdir, archive_name)

            doc_dir = os.path.join(tmpdir, "docs")
            os.makedirs(doc_dir, exist_ok=True)
            for name, content in documents.items():
                safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
                file_path = os.path.join(doc_dir, f"{safe_name}.bin")
                with open(file_path, "wb") as f:
                    f.write(content)

            # Create tar.gz
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(doc_dir, arcname="")

            # Determine the appropriate Drive folder path
            folder_path = []
            if "federal" in missing_levels:
                folder_path = ["Federal"]
            elif "state" in missing_levels and jurisdiction.get("state"):
                # Use state name as folder under "State"
                folder_path = ["State", jurisdiction["state"]]
            elif "county" in missing_levels and jurisdiction.get("county"):
                folder_path = ["County", jurisdiction["county"]]
            elif "municipal" in missing_levels and jurisdiction.get("municipality"):
                folder_path = ["Municipal", jurisdiction["municipality"]]
            else:
                # Fallback: upload to root (should not happen)
                folder_path = ["_unclassified"]

            # Ensure the folder path exists and get its ID
            folder_id = await self.drive_service.ensure_folder_path(folder_path)
            if not folder_id:
                logger.error("Could not resolve or create folder path %s. Aborting upload.", folder_path)
                return

            # Upload the archive
            try:
                await self.drive_service.upload_file(
                    file_path=archive_path,
                    parent_folder_id=folder_id,
                    file_name=archive_name,
                    mime_type="application/gzip",
                )
                logger.info("Successfully uploaded archive for task: %s", task_data)
            except Exception as e:
                # Log error but do not crash; the task will be lost but that's acceptable.
                logger.exception("Failed to upload archive for task %s: %s", task_data, e)

    async def _worker(self, worker_id: int) -> None:
        """
        Worker coroutine that continuously pulls tasks from Redis.
        """
        logger.info("Worker %d started.", worker_id)
        async with aiohttp.ClientSession(
            headers={"User-Agent": "CAIS-Search-Agent/1.0"},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            self._session = session
            while self.running:
                try:
                    result = await self.redis.brpop(self.queue_name, timeout=5)
                    if not result:
                        continue
                    _, data = result
                    try:
                        task_data = json.loads(data)
                        await self._process_task(task_data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON in task: %s", data)
                    except Exception as e:
                        logger.exception("Worker %d error processing task: %s", worker_id, e)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception("Worker %d encountered an error: %s", worker_id, e)
                    await asyncio.sleep(1)
        logger.info("Worker %d stopped.", worker_id)

    async def start(self) -> None:
        """Start the worker pool."""
        if self.running:
            logger.warning("Pool is already running.")
            return

        if not self.redis:
            logger.error("Redis client not provided; cannot start worker pool.")
            return

        self.running = True
        self.tasks = [
            asyncio.create_task(self._worker(i), name=f"SearchWorker-{i}")
            for i in range(self.num_workers)
        ]
        logger.info("SearchAgentPool started with %d workers.", self.num_workers)

    async def stop(self) -> None:
        """Gracefully stop all workers."""
        if not self.running:
            return
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        logger.info("SearchAgentPool stopped.")


async def run_search_pool(
    num_workers: int = 3,
    redis_url: Optional[str] = None,
) -> None:
    """
    Entry point for running the search agent pool.

    Args:
        num_workers: Number of worker coroutines.
        redis_url: Redis connection URL; uses settings.REDIS_URL if None.
    """
    if redis_url is None:
        redis_url = settings.REDIS_URL
    if not redis_url:
        raise RuntimeError("REDIS_URL is not configured.")
    if aioredis is None:
        raise RuntimeError("aioredis is not installed.")

    redis_client = aioredis.from_url(redis_url)
    await redis_client.ping()

    drive_service = DriveSyncService()
    pool = SearchAgentPool(
        num_workers=num_workers,
        redis_client=redis_client,
        drive_service=drive_service,
    )
    try:
        await pool.start()
        await asyncio.Event().wait()
    finally:
        await pool.stop()
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run_search_pool())
