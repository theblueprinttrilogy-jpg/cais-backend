"""
app/workers/ingestion_worker.py

Background ingestion worker for CAIS Code Compliance backend.
Continuously runs an ingestion loop that uses the AutonomousOrchestrator
to fetch and store code references for key jurisdictions and topics.
"""

import logging
import time
import signal
import sys
from typing import List, Optional

# Import the orchestrator from the agents module
from app.agents.orchestrator import AutonomousOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default sleep interval between ingestion cycles (in seconds)
DEFAULT_SLEEP_INTERVAL = 300  # 5 minutes

# List of target jurisdictions/topics to ingest
# These can be expanded or configured via environment variables
DEFAULT_TARGETS = [
    "Florida Building Code",
    "International Residential Code",
    "fire safety",
    "structural wind loads",
    "electrical standards",
    "California Title 24",
    "New York City Building Code",
    "ASHRAE 90.1",
    "NFPA 70",
    "International Energy Conservation Code",
]


class IngestionWorker:
    """
    Continuous background worker that runs ingestion cycles at regular intervals.
    """

    def __init__(
        self,
        targets: Optional[List[str]] = None,
        sleep_interval: int = DEFAULT_SLEEP_INTERVAL,
    ):
        """
        Initialize the worker with a list of targets and a sleep interval.

        :param targets: List of query strings to ingest. If None, uses DEFAULT_TARGETS.
        :param sleep_interval: Time in seconds to sleep between cycles.
        """
        self.targets = targets if targets is not None else DEFAULT_TARGETS
        self.sleep_interval = sleep_interval
        self.running = True
        self.orchestrator: Optional[AutonomousOrchestrator] = None

        logger.info(
            f"IngestionWorker initialized with {len(self.targets)} targets "
            f"and sleep interval {self.sleep_interval}s."
        )

    def _initialize_orchestrator(self) -> None:
        """Create a new instance of the AutonomousOrchestrator."""
        try:
            self.orchestrator = AutonomousOrchestrator()
            logger.info("Orchestrator instantiated successfully.")
        except Exception as e:
            logger.error(f"Failed to instantiate orchestrator: {e}")
            self.orchestrator = None

    def _run_ingestion_cycle(self) -> None:
        """
        Execute one full ingestion cycle:
          - For each target, call orchestrator.ingest(target).
          - Log the results.
        """
        if self.orchestrator is None:
            logger.error("Orchestrator not available. Skipping ingestion cycle.")
            return

        logger.info("Starting new ingestion cycle.")
        total_stored = 0
        for target in self.targets:
            try:
                logger.info(f"Ingesting target: '{target}'")
                stored_records = self.orchestrator.ingest(target)
                count = len(stored_records)
                total_stored += count
                logger.info(
                    f"Ingestion for '{target}' completed. Stored {count} records."
                )
            except Exception as e:
                logger.error(
                    f"Ingestion for target '{target}' failed with exception: {e}",
                    exc_info=True
                )
                # Continue with next target despite failure

        logger.info(
            f"Ingestion cycle completed. Total records stored across all targets: {total_stored}"
        )

    def run(self) -> None:
        """
        Main worker loop: runs continuously until stopped.
        Each iteration performs a full ingestion cycle and then sleeps.
        """
        logger.info("IngestionWorker starting main loop.")
        self._initialize_orchestrator()

        while self.running:
            try:
                self._run_ingestion_cycle()
            except Exception as e:
                logger.error(
                    f"Unexpected error during ingestion cycle: {e}",
                    exc_info=True
                )
                # Even if a severe error occurs, we continue the loop
                # after sleeping to avoid busy-looping.

            # Sleep for the configured interval, but check for stop signal periodically
            logger.info(f"Worker sleeping for {self.sleep_interval} seconds.")
            for _ in range(self.sleep_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("IngestionWorker main loop terminated.")

    def stop(self) -> None:
        """Signal the worker to stop after the current cycle completes."""
        logger.info("Stop signal received. Worker will shut down.")
        self.running = False


# Signal handler for graceful shutdown
def signal_handler(signum, frame) -> None:
    """Handle SIGTERM and SIGINT to stop the worker gracefully."""
    logger.info(f"Received signal {signum}. Initiating shutdown.")
    # The worker's stop method will be called from the main thread
    # We set a global flag or use an event; here we rely on the main loop
    # checking the running flag. We need a reference to the worker instance.
    # Since this is a simple script, we use a global variable.
    global worker_instance
    if worker_instance:
        worker_instance.stop()


# Global reference for signal handler
worker_instance: Optional[IngestionWorker] = None


def main() -> None:
    """Entry point for the ingestion worker."""
    global worker_instance

    # Register signal handlers for graceful termination
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Parse command-line arguments (optional)
    # For simplicity, we use environment variables or defaults.
    import os
    sleep_interval = int(os.getenv("INGESTION_SLEEP_INTERVAL", DEFAULT_SLEEP_INTERVAL))
    targets_env = os.getenv("INGESTION_TARGETS")
    if targets_env:
        targets = [t.strip() for t in targets_env.split(",") if t.strip()]
    else:
        targets = DEFAULT_TARGETS

    worker = IngestionWorker(targets=targets, sleep_interval=sleep_interval)
    worker_instance = worker

    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
        worker.stop()
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if worker.orchestrator:
            worker.orchestrator.close()
        logger.info("Worker shut down successfully.")


if __name__ == "__main__":
    main()
