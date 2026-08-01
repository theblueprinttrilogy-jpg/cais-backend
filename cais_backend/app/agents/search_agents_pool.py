"""
SearchAgentPool – Manages concurrent search agents that download building codes,
regulations, and laws from various sources.

Each agent processes a jurisdiction task, downloads relevant PDFs from known sources
(e.g., OSHA, IBC, NFPA, state portals), and uploads them to Google Drive using rclone.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def upload_with_rclone(local_path: Path, remote_path: str) -> bool:
    """
    Upload a file to Google Drive using rclone.
    Uses the configured remote 'gdrive-sa:' which points to the account
    theblueprinttrilogy@gmail.com.

    Args:
        local_path: Local file path.
        remote_path: Destination path inside CAIS_CONSTRUCTION_FILES, e.g. "USA/California/ibc.pdf"

    Returns:
        True if upload succeeded, False otherwise.
    """
    cmd = [
        "rclone", "copy",
        str(local_path),
        f"gdrive-sa:CAIS_CONSTRUCTION_FILES/{remote_path}",
        "--drive-chunk-size", "64M",
        "--verbose"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"rclone upload failed for {local_path.name}: {result.stderr}")
            return False
        logger.info(f"Uploaded {local_path.name} to {remote_path}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"rclone upload timed out for {local_path.name}")
        return False
    except Exception as e:
        logger.exception(f"rclone upload exception for {local_path.name}: {e}")
        return False


class SearchAgentPool:
    """
    Pool of search agents that process jurisdiction tasks from Redis.
    """

    # Known sources for each jurisdiction (expandable)
    SOURCES = {
        "OSHA": {
            "url": "https://www.osha.gov/laws-regs/regulations",
            "type": "regulation",
            "selector": "a[href$='.pdf']"
        },
        # Add more sources here (IBC, NFPA, state portals, etc.)
        # "IBC": {
        #     "url": "https://codes.iccsafe.org/content/IBC2024",
        #     "type": "code",
        #     "selector": "a[href$='.pdf']"
        # },
    }

    def __init__(
        self,
        num_workers: int = 3,
        redis_client: Optional[Any] = None,
        drive_service: Optional[Any] = None,  # Kept for compatibility
        **kwargs
    ):
        """
        Args:
            num_workers: Number of concurrent workers.
            redis_client: Redis client for consuming tasks from queue.
            drive_service: Kept for compatibility (not used, rclone handles uploads).
        """
        self.num_workers = num_workers
        self.redis_client = redis_client
        self.queue_key = "cais:search:queue"
        self.workers = []
        self.running = False
        self._stop_event = asyncio.Event()
        self.drive_service = drive_service  # Kept for compatibility

    async def start(self):
        """Start the worker pool."""
        if not self.redis_client:
            logger.error("Redis client not provided. SearchAgentPool cannot start.")
            return

        self.running = True
        self._stop_event.clear()
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker)
            logger.info(f"Worker {i} started.")

    async def stop(self):
        """Stop all workers."""
        self.running = False
        self._stop_event.set()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("SearchAgentPool stopped.")

    async def _worker_loop(self, worker_id: int):
        """Main loop for a worker, consuming from Redis."""
        logger.info(f"Worker {worker_id} started, waiting for tasks from Redis...")
        while self.running:
            try:
                # Pop a task from Redis with timeout
                result = await self.redis_client.blpop(self.queue_key, timeout=5)
                if result is None:
                    continue

                _, task_data_raw = result
                task_data = json.loads(task_data_raw)
                logger.info(f"Worker {worker_id} processing task: {task_data}")

                await self._process_task(task_data, worker_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped.")

    async def _process_task(self, task_data: Dict[str, Any], worker_id: int):
        """
        Process a single jurisdiction task.
        Downloads PDFs from known sources and uploads them to Drive.
        """
        state = task_data.get('state', 'unknown')
        country = task_data.get('country', 'United States')
        missing_levels = task_data.get('missing_levels', [])

        logger.info(f"Worker {worker_id} processing task for {state} - missing: {missing_levels}")

        # For each source, attempt to download
        for source_name, source_info in self.SOURCES.items():
            try:
                pdfs = await self._fetch_pdfs(source_info['url'], source_info.get('selector', 'a[href$=".pdf"]'))
                logger.info(f"Worker {worker_id} found {len(pdfs)} PDFs from {source_name} for {state}")

                for pdf_url, pdf_name in pdfs:
                    local_path = await self._download_pdf(pdf_url, pdf_name, state)
                    if local_path:
                        remote_path = f"{country}/{state}/{source_name}/{pdf_name}"
                        success = upload_with_rclone(local_path, remote_path)
                        if success:
                            # Clean up local file after successful upload
                            try:
                                local_path.unlink()
                            except:
                                pass
            except Exception as e:
                logger.warning(f"Worker {worker_id} error fetching from {source_name} for {state}: {e}")

        # Also try to fetch from state-specific portals if known
        await self._fetch_state_portal(state, country, worker_id)

    async def _fetch_pdfs(self, url: str, selector: str) -> List[tuple]:
        """
        Fetch PDF links from a given URL using BeautifulSoup.
        Returns a list of (url, filename) tuples.
        """
        pdfs = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return []
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for link in soup.select(selector):
                        href = link.get('href')
                        if not href:
                            continue
                        if not href.endswith('.pdf'):
                            continue
                        # Ensure absolute URL
                        if href.startswith('/'):
                            href = url.rstrip('/') + href
                        elif not href.startswith('http'):
                            href = url.rstrip('/') + '/' + href
                        name = href.split('/')[-1]
                        pdfs.append((href, name))
            return pdfs
        except Exception as e:
            logger.error(f"Error fetching PDFs from {url}: {e}")
            return []

    async def _download_pdf(self, url: str, filename: str, state: str) -> Optional[Path]:
        """
        Download a single PDF and save it to a temporary location.
        Returns the Path to the downloaded file, or None on failure.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to download {url}: {response.status}")
                        return None
                    # Create temp directory for the state
                    temp_dir = Path(f"/tmp/cais_pdfs/{state}")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    local_path = temp_dir / filename
                    with open(local_path, 'wb') as f:
                        f.write(await response.read())
                    logger.info(f"Downloaded {filename} to {local_path}")
                    return local_path
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    async def _fetch_state_portal(self, state: str, country: str, worker_id: int):
        """
        Placeholder for state-specific portal scraping.
        Expand with known state portals.
        """
        # Known state portals (expand this dictionary)
        STATE_PORTALS = {
            "California": "https://www.dgs.ca.gov/BSC/Codes",
            "Texas": "https://www.tdlr.texas.gov/buildingcodes.htm",
            "Florida": "https://www.floridabuilding.org/",
            "New York": "https://www.dos.ny.gov/dcea/",
            # Add more states as needed
        }

        portal_url = STATE_PORTALS.get(state)
        if not portal_url:
            logger.warning(f"No known portal for state: {state}")
            return

        try:
            pdfs = await self._fetch_pdfs(portal_url, 'a[href$=".pdf"]')
            if not pdfs:
                logger.warning(f"No PDFs found at {portal_url} for {state}")
                return
            logger.info(f"Worker {worker_id} found {len(pdfs)} PDFs from state portal for {state}")
            for pdf_url, pdf_name in pdfs:
                local_path = await self._download_pdf(pdf_url, pdf_name, state)
                if local_path:
                    remote_path = f"{country}/{state}/StatePortal/{pdf_name}"
                    success = upload_with_rclone(local_path, remote_path)
                    if success:
                        try:
                            local_path.unlink()
                        except:
                            pass
        except Exception as e:
            logger.warning(f"Worker {worker_id} error fetching state portal for {state}: {e}")
