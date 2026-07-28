#!/usr/bin/env python3
"""
Live integration test for the DriveSyncService.

This script initializes the Google Drive service using the configured credentials
and attempts to list files in a specified folder (default: ROOT_FOLDER_ID from env)
to verify connectivity and authentication.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to sys.path so that app modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.drive_sync_service import DriveSyncService
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the live integration test."""
    logger.info("Starting Google Drive live integration test")

    # Determine which folder to list
    folder_id = getattr(settings, "ROOT_FOLDER_ID", None)
    if not folder_id:
        logger.warning("ROOT_FOLDER_ID not set in settings; using root folder 'root'")
        folder_id = "root"

    try:
        # Initialize the DriveSyncService (this will authenticate)
        logger.info("Creating DriveSyncService instance...")
        service = DriveSyncService()
        logger.info("Service created successfully, attempting to list files...")

        # List files in the specified folder (limit to 10 for sanity)
        files = await service.list_files(folder_id, page_size=10)
        logger.info("Successfully listed %d file(s) in folder %s", len(files), folder_id)
        for f in files[:5]:  # print first 5
            logger.info(
                "File: %s (ID: %s, modified: %s)",
                f.get("name"),
                f.get("id"),
                f.get("modifiedTime"),
            )
        if len(files) > 5:
            logger.info("... and %d more", len(files) - 5)

        logger.info("Integration test completed successfully.")
        return 0

    except Exception as e:
        logger.exception("Integration test failed: %s", e)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
