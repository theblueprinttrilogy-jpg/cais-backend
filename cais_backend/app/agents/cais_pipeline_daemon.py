"""
app/agents/cais_pipeline_daemon.py

CAIS Continuous Pipeline Daemon with Telegram Natural Language Alerts.

This autonomous background daemon continuously runs the Dictionary Downloader Agent
(unlimited global languages) and the Dual-Account Google Drive Archiver Agent in a
robust background loop. It provides comprehensive logging, graceful shutdown handling,
and instant Telegram alerts on fatal errors.

Configuration is provided via CLI arguments or environment variables.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

# Import the agents (adjust imports based on actual module structure)
from app.agents.dictionary_downloader import DictionaryDownloaderAgent
from app.agents.dictionary_drive_archiver import DictionaryDriveArchiverAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default sleep interval (24 hours)
DEFAULT_INTERVAL_SECONDS = 86400
# Telegram API endpoint
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class CAISPipelineDaemon:
    """
    Autonomous daemon that orchestrates the dictionary download and archive pipeline.
    """

    def __init__(
        self,
        downloader_config: Dict[str, Any],
        archiver_config: Dict[str, Any],
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        """
        Initialize the daemon with configuration.

        :param downloader_config: Configuration dict for DictionaryDownloaderAgent.
        :param archiver_config: Configuration dict for DictionaryDriveArchiverAgent.
        :param interval_seconds: Time to sleep between pipeline runs.
        :param telegram_token: Telegram Bot Token for alerts.
        :param telegram_chat_id: Telegram Chat ID for alerts.
        """
        self.downloader_config = downloader_config
        self.archiver_config = archiver_config
        self.interval_seconds = interval_seconds
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id

        self._running = True
        self._pipeline_name = "CAIS Dictionary Pipeline"

    # ------------------------------------------------------------------
    # Telegram Alerting
    # ------------------------------------------------------------------
    def _send_telegram_alert(self, message: str) -> None:
        """
        Send an alert message via Telegram Bot API.
        If token or chat_id is missing, log a warning and do nothing.
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured. Alert not sent.")
            return

        try:
            url = TELEGRAM_API_URL.format(token=self.telegram_token)
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    def _format_error_alert(self, error: Exception, context: str = "") -> str:
        """
        Format a natural language alert message for a fatal error.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"🚨 *{self._pipeline_name} - FATAL ERROR*",
            f"⏰ *Time:* {timestamp}",
            f"📌 *Context:* {context}",
            f"⚠️ *Error Type:* {error_type}",
            f"📝 *Message:* {error_msg}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Pipeline Execution
    # ------------------------------------------------------------------
    def _run_downloader(self) -> Dict[str, Any]:
        """
        Execute the DictionaryDownloaderAgent with its configuration.
        """
        logger.info("Starting Dictionary Downloader Agent...")
        agent = DictionaryDownloaderAgent(**self.downloader_config)
        result = agent.run()
        logger.info("Dictionary Downloader Agent finished.")
        return result

    def _run_archiver(self) -> Dict[str, Any]:
        """
        Execute the DictionaryDriveArchiverAgent with its configuration.
        """
        logger.info("Starting Dictionary Drive Archiver Agent...")
        agent = DictionaryDriveArchiverAgent(**self.archiver_config)
        result = agent.run()
        logger.info("Dictionary Drive Archiver Agent finished.")
        return result

    def _run_pipeline(self) -> None:
        """
        Execute the full pipeline: downloader then archiver.
        Any unhandled exception will be caught and escalated.
        """
        # Step 1: Download dictionaries
        try:
            download_summary = self._run_downloader()
            logger.info(f"Downloader summary: {json.dumps(download_summary, indent=2)}")
        except Exception as e:
            # Fatal error in downloader
            alert_msg = self._format_error_alert(e, context="Dictionary Downloader")
            self._send_telegram_alert(alert_msg)
            # Re-raise to stop the pipeline run (but daemon will continue after sleep)
            raise

        # Step 2: Archive and upload
        try:
            archiver_summary = self._run_archiver()
            logger.info(f"Archiver summary: {json.dumps(archiver_summary, indent=2)}")
        except Exception as e:
            alert_msg = self._format_error_alert(e, context="Dictionary Archiver")
            self._send_telegram_alert(alert_msg)
            raise

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """
        Start the daemon's main loop.
        Continuously runs the pipeline at the configured interval.
        Handles SIGINT and SIGTERM for graceful shutdown.
        """
        # Set up signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down gracefully...")
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info(f"CAIS Pipeline Daemon started. Interval: {self.interval_seconds}s")
        logger.info("Press Ctrl+C to stop.")

        while self._running:
            try:
                self._run_pipeline()
            except Exception as e:
                # Pipeline run failed; alert already sent. We log and continue after sleep.
                logger.error(f"Pipeline run failed: {e}")
                # Optionally, send a second alert if the first was not sent? Already sent inside.

            # Sleep until next run, but check if we should stop periodically
            if self._running and self.interval_seconds > 0:
                logger.info(f"Sleeping for {self.interval_seconds} seconds until next run.")
                # Sleep in small increments to allow signal handling
                sleep_remaining = self.interval_seconds
                while sleep_remaining > 0 and self._running:
                    time.sleep(min(10, sleep_remaining))
                    sleep_remaining -= 10

        logger.info("CAIS Pipeline Daemon stopped.")


# ================================================================
# CLI Entry Point
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="CAIS Continuous Pipeline Daemon with Telegram Alerts"
    )

    # Downloader arguments
    parser.add_argument(
        "--downloader-output-dir",
        default="/tmp/cais_dictionaries/raw",
        help="Output directory for raw dictionaries",
    )
    parser.add_argument(
        "--downloader-max-sources",
        type=int,
        default=None,
        help="Maximum sources to process (default: unlimited)",
    )
    parser.add_argument(
        "--downloader-headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--downloader-no-headless",
        dest="downloader_headless",
        action="store_false",
        help="Disable headless mode",
    )

    # Archiver primary account (required)
    parser.add_argument("--primary-client-id", required=True, help="Primary OAuth2 client ID")
    parser.add_argument("--primary-client-secret", required=True, help="Primary OAuth2 client secret")
    parser.add_argument("--primary-refresh-token", required=True, help="Primary OAuth2 refresh token")
    parser.add_argument("--primary-folder-id", help="Primary Drive folder ID")

    # Archiver backup account (optional)
    parser.add_argument("--backup-client-id", help="Backup OAuth2 client ID")
    parser.add_argument("--backup-client-secret", help="Backup OAuth2 client secret")
    parser.add_argument("--backup-refresh-token", help="Backup OAuth2 refresh token")
    parser.add_argument("--backup-folder-id", help="Backup Drive folder ID")

    # Archiver directories
    parser.add_argument(
        "--archiver-raw-dir",
        default="/tmp/cais_dictionaries/raw",
        help="Directory containing raw dictionary files (default: /tmp/cais_dictionaries/raw)",
    )
    parser.add_argument(
        "--archiver-archive-dir",
        default="/tmp/cais_dictionaries",
        help="Directory to store the generated .zip archive (default: /tmp/cais_dictionaries)",
    )

    # Daemon settings
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help=f"Sleep interval between runs in seconds (default: {DEFAULT_INTERVAL_SECONDS})",
    )

    # Telegram alert settings
    parser.add_argument(
        "--telegram-token",
        default=os.getenv("TELEGRAM_BOT_TOKEN"),
        help="Telegram Bot Token (can also set TELEGRAM_BOT_TOKEN env var)",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("TELEGRAM_CHAT_ID"),
        help="Telegram Chat ID (can also set TELEGRAM_CHAT_ID env var)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    # Prepare downloader config
    downloader_config = {
        "output_dir": args.downloader_output_dir,
        "max_sources": args.downloader_max_sources,
        "headless": args.downloader_headless,
    }

    # Prepare archiver config
    archiver_config = {
        "primary_client_id": args.primary_client_id,
        "primary_client_secret": args.primary_client_secret,
        "primary_refresh_token": args.primary_refresh_token,
        "primary_folder_id": args.primary_folder_id,
        "backup_client_id": args.backup_client_id,
        "backup_client_secret": args.backup_client_secret,
        "backup_refresh_token": args.backup_refresh_token,
        "backup_folder_id": args.backup_folder_id,
        "raw_dir": args.archiver_raw_dir,
        "archive_dir": args.archiver_archive_dir,
    }

    # Validate that if backup credentials are provided, all three are present
    backup_provided = any([args.backup_client_id, args.backup_client_secret, args.backup_refresh_token])
    if backup_provided:
        if not (args.backup_client_id and args.backup_client_secret and args.backup_refresh_token):
            logger.error("If providing backup credentials, all three (client-id, client-secret, refresh-token) are required.")
            sys.exit(1)

    # Create and run daemon
    daemon = CAISPipelineDaemon(
        downloader_config=downloader_config,
        archiver_config=archiver_config,
        interval_seconds=args.interval,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat_id,
    )

    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Daemon interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Daemon crashed: {e}", exc_info=True)
        # Attempt to send alert from main if daemon itself fails
        if args.telegram_token and args.telegram_chat_id:
            try:
                msg = f"🚨 *CAIS Daemon Crashed*\nError: {str(e)}"
                url = TELEGRAM_API_URL.format(token=args.telegram_token)
                requests.post(url, json={"chat_id": args.telegram_chat_id, "text": msg}, timeout=10)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
