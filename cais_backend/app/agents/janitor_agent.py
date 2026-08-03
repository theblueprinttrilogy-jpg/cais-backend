import asyncio
import logging
from typing import Any, Dict, Optional

from app.agents.base import BaseAgent
from app.db.session import async_session_factory
from app.services.drive import GoogleDriveService
from app.services.janitor import JanitorService

logger = logging.getLogger(__name__)


class JanitorAgent(BaseAgent):
    """
    Agent responsible for running janitorial cleanup tasks, such as
    purging expired soft-deleted files and removing orphan records.
    """

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        retention_days: int = 30,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the JanitorAgent.

        :param credentials_file: Path to Google Drive service account
                                 credentials JSON file. If provided, it
                                 will be used to initialize the drive
                                 service. If None, default credentials
                                 are used.
        :param retention_days: Number of days to retain soft-deleted files.
        :param args: Additional positional arguments (ignored).
        :param kwargs: Additional keyword arguments (ignored).
        """
        # Call super without any arguments to avoid passing to object.__init__
        super().__init__()
        self.credentials_file = credentials_file
        self.retention_days = retention_days
        self._drive_service: Optional[GoogleDriveService] = None

    async def initialize(self) -> None:
        """
        Asynchronously initialize the Google Drive service and any
        other resources needed by this agent.
        """
        logger.info("Initializing JanitorAgent")
        # Build the drive service; this may involve reading credentials
        # which can be IO-bound, but we can do it here since it's async.
        self._drive_service = GoogleDriveService(
            credentials_path=self.credentials_file
        )
        logger.info("JanitorAgent initialized successfully")

    async def execute(self, input_data: Any) -> Dict[str, Any]:
        """
        Execute the janitor cleanup routine.

        The input_data may contain:
            - "retention_days": Override the default retention period.
            - "clean_orphans": Boolean, if True also run orphan cleanup.

        If input_data is not a dictionary (e.g., list, None, etc.), it is
        coerced to an empty dictionary to prevent AttributeError.

        :param input_data: Input parameters, expected to be a dict.
        :return: Dictionary with cleanup results.
        """
        # Normalize input_data to a dict
        if not isinstance(input_data, dict):
            logger.warning(
                f"Received non-dict input_data of type {type(input_data)}. "
                "Coercing to empty dict."
            )
            input_data = {}

        logger.info("JanitorAgent executing cleanup")
        # Override retention days if provided
        retention_days = input_data.get("retention_days", self.retention_days)
        clean_orphans = input_data.get("clean_orphans", False)

        # Create a fresh async session for this operation
        async with async_session_factory() as session:
            # Instantiate the janitor service with the session
            janitor = JanitorService(
                db_session=session,
                drive_service=self._drive_service,
                retention_days=retention_days,
            )

            # Run the main cleanup
            purged_count = await janitor.run_cleanup()
            result = {
                "purged_files": purged_count,
                "orphan_cleanup_run": False,
            }

            # Optionally run orphan cleanup
            if clean_orphans:
                orphan_count = await janitor.run_orphan_cleanup()
                result["orphan_cleanup_run"] = True
                result["orphan_files_purged"] = orphan_count

            logger.info(
                f"JanitorAgent cleanup completed: {result}"
            )
            return result

    def run_sweep(self, input_data: Any = None) -> Dict[str, Any]:
        """
        Synchronous entry point for janitor sweep, required by JanitorDaemon.

        This method uses asyncio.run() to execute the asynchronous execute()
        method and returns the resulting dictionary of JSON-serializable
        primitives. It must be called from a thread without a running event loop;
        otherwise, a RuntimeError is raised.

        Input data is normalized: if input_data is not a dict, it is coerced
        to an empty dictionary before passing to execute.

        :param input_data: Optional input parameters.
        :return: Result dictionary from the cleanup.
        """
        # Normalize input_data to a dict (or None is handled by execute)
        if not isinstance(input_data, dict):
            logger.warning(
                f"run_sweep received non-dict input_data of type {type(input_data)}. "
                "Coercing to empty dict."
            )
            input_data = {}
        return asyncio.run(self.execute(input_data))

    async def shutdown(self) -> None:
        """
        Clean up resources used by the agent.
        """
        logger.info("Shutting down JanitorAgent")
        # Any cleanup needed for drive service, etc.
        if self._drive_service:
            # Assume drive_service has a close method if needed
            pass
        logger.info("JanitorAgent shut down")
