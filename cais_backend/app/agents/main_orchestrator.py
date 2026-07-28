"""
CAIS Main Orchestrator.

Coordinates the concurrent execution of:
- JanitorAgent (continuous storage hygiene)
- GlobalJurisdictionAgent (gap analysis and search triggers)
- SearchAgentPool (real web scraping of regulatory documents)
- DriveSyncService (local mock storage synchronization)

Handles graceful shutdown and structured logging.

IMPORTANT: At import time, this module patches aiohttp.helpers to provide
a missing `urldefrag` attribute for compatibility with Python 3.12
and newer aiohttp versions.
"""

# -----------------------------------------------------------------------------
# PATCH: aiohttp.helpers.urldefrag for Python 3.12 compatibility
# -----------------------------------------------------------------------------
import sys
import importlib
import warnings

try:
    import aiohttp.helpers
    if not hasattr(aiohttp.helpers, "urldefrag"):
        from urllib.parse import urldefrag as _urldefrag

        def _patched_urldefrag(url):
            return _urldefrag(url)

        setattr(aiohttp.helpers, "urldefrag", _patched_urldefrag)
        warnings.warn(
            "Patched missing aiohttp.helpers.urldefrag for compatibility.",
            RuntimeWarning,
            stacklevel=2,
        )
except ImportError:
    # aiohttp not installed, ignore
    pass
# -----------------------------------------------------------------------------

import asyncio
import logging
import signal
import sys
from typing import Optional, Any

from app.agents.janitor_agent import JanitorAgent
from app.agents.global_jurisdiction_agent import GlobalJurisdictionAgent
from app.agents.search_agents_pool import SearchAgentPool
from app.services.drive_sync_service import DriveSyncService  # mock local storage
from app.services.zip_code_service import ZipCodeService
from app.core.config import settings

# Optional Redis client for orchestration
try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Master orchestrator that initializes and runs all CAIS backend agents
    and services concurrently.

    Attributes:
        janitor_agent (JanitorAgent): The janitor agent instance.
        global_agent (GlobalJurisdictionAgent): The jurisdiction agent.
        search_pool (SearchAgentPool): The search worker pool.
        drive_service (DriveSyncService): The Drive sync service (mock/local).
        redis_client (Optional[aioredis.Redis]): Redis client for queue communication.
        tasks (List[asyncio.Task]): List of running task coroutines.
        shutdown_event (asyncio.Event): Event to signal shutdown.
    """

    def __init__(self):
        self.janitor_agent: Optional[JanitorAgent] = None
        self.global_agent: Optional[GlobalJurisdictionAgent] = None
        self.search_pool: Optional[SearchAgentPool] = None
        self.drive_service: Optional[DriveSyncService] = None
        self.redis_client: Optional[Any] = None
        self.tasks: list[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()

    async def _init_redis(self) -> None:
        """Initialise Redis client if configured."""
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL not set; Redis functionality disabled.")
            return
        if aioredis is None:
            logger.warning("aioredis not installed; Redis functionality disabled.")
            return
        try:
            self.redis_client = aioredis.from_url(settings.REDIS_URL)
            await self.redis_client.ping()
            logger.info("Connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            self.redis_client = None

    async def _init_services(self) -> None:
        """Initialise all services and agents."""
        # Drive service (mock local storage)
        self.drive_service = DriveSyncService()
        logger.info("DriveSyncService (mock) initialised at %s", self.drive_service.base_path)

        # ZipCodeService (depends on Drive service)
        zip_service = ZipCodeService(self.drive_service)
        logger.info("ZipCodeService initialised.")

        # Janitor agent (continuous mode)
        self.janitor_agent = JanitorAgent(
            continuous=True,
            sweep_interval=getattr(settings, "JANITOR_SWEEP_INTERVAL", 3600),
            dry_run=getattr(settings, "JANITOR_DRY_RUN", False),
        )
        logger.info("JanitorAgent initialised.")

        # GlobalJurisdictionAgent (depends on Drive, Zip, and Redis)
        self.global_agent = GlobalJurisdictionAgent(
            drive_service=self.drive_service,
            zip_code_service=zip_service,
            redis_client=self.redis_client,
        )
        logger.info("GlobalJurisdictionAgent initialised.")

        # SearchAgentPool (requires Redis and Drive)
        if self.redis_client:
            self.search_pool = SearchAgentPool(
                num_workers=getattr(settings, "SEARCH_POOL_WORKERS", 3),
                redis_client=self.redis_client,
                drive_service=self.drive_service,
                rate_limit=getattr(settings, "SEARCH_RATE_LIMIT", 5),
            )
            logger.info("SearchAgentPool initialised.")
        else:
            logger.warning("Redis not available; SearchAgentPool will not start.")

    async def _run_janitor(self) -> None:
        """Run the janitor agent (blocking)."""
        await self.janitor_agent.start()

    async def _run_global_agent(self) -> None:
        """Run the global jurisdiction agent in a loop."""
        interval = getattr(settings, "GLOBAL_AGENT_INTERVAL", 21600)  # 6 hours
        while not self.shutdown_event.is_set():
            try:
                await self.global_agent.run_sync_cycle()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in global agent cycle: %s", e)
                await asyncio.sleep(60)  # back off

    async def _run_search_pool(self) -> None:
        """
        Run the search agent pool (continuous worker loop).
        """
        if not self.search_pool:
            logger.warning("SearchAgentPool not available; skipping.")
            return
        try:
            await self.search_pool.start()
            # Wait for shutdown signal
            await self.shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Search pool task cancelled.")
        except Exception as e:
            logger.exception("Search pool error: %s", e)
        finally:
            if self.search_pool:
                await self.search_pool.stop()

    async def _run_drive_sync(self) -> None:
        """
        Periodically sync with Drive (mock) to check for new documents.
        """
        interval = getattr(settings, "DRIVE_SYNC_INTERVAL", 1800)  # 30 minutes
        while not self.shutdown_event.is_set():
            try:
                # The DriveSyncService is already used by other agents.
                # We can optionally scan for changes, but not required.
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Drive sync error: %s", e)
                await asyncio.sleep(60)

    def _signal_handler(self, sig, frame):
        """Handle SIGINT/SIGTERM by setting shutdown event."""
        logger.info("Received signal %s, shutting down...", sig)
        self.shutdown_event.set()

    async def run(self) -> None:
        """Start all agents and wait for shutdown."""
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler, sig, None)

        # Initialise services
        await self._init_redis()
        await self._init_services()

        # Create tasks for all concurrent components
        self.tasks = [
            asyncio.create_task(self._run_janitor(), name="JanitorAgent"),
            asyncio.create_task(self._run_global_agent(), name="GlobalJurisdictionAgent"),
            asyncio.create_task(self._run_search_pool(), name="SearchPool"),
            asyncio.create_task(self._run_drive_sync(), name="DriveSync"),
        ]

        logger.info("Master orchestrator started with %d tasks.", len(self.tasks))

        # Wait for shutdown signal
        await self.shutdown_event.wait()

        # Cancel all tasks and wait for them to finish
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("All tasks cancelled.")

        # Clean up Redis connection
        if self.redis_client:
            await self.redis_client.close()

        logger.info("Master orchestrator shut down gracefully.")

    async def stop(self) -> None:
        """Signal shutdown and wait for cleanup."""
        self.shutdown_event.set()
        await asyncio.sleep(1)
        if self.tasks:
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Orchestrator stopped.")


# Global instance for easy import
orchestrator = MasterOrchestrator()


async def main():
    """Entry point for running the orchestrator."""
    await orchestrator.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting.")
        sys.exit(0)
