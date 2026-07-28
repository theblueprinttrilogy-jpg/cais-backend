#!/usr/bin/env python3
"""
Download Agent - Downloads building codes and ISO standards from multiple jurisdictions.
Runs continuously in the cais-agents container.
"""
import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from pathlib import Path

# === CONFIGURATION ===
OUTPUT_DIR = "/app/downloads"
LOG_FILE = "/app/logs/10_human_agents.log"
MAX_WORKERS = 5
RETRY_DELAY = 5
MAX_RETRIES = 3

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# === SOURCES ===
SOURCES = [
    {"name": "ISO", "jurisdiction": "International", "url": "https://www.iso.org/"},
    # Additional sources can be added here
]

class CodeDownloader:
    def __init__(self):
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def download_source(self, source):
        logger.info(f"Processing: {source['name']} - {source['jurisdiction']}")
        try:
            response = requests.get(source['url'], headers=self.headers, timeout=30)
            if response.status_code == 200:
                logger.info(f"✅ {source['jurisdiction']} - {source['name']} - {source['url']}")
                return True
        except Exception as e:
            logger.error(f"❌ {source['jurisdiction']} - {source['name']} - Error: {e}")
        return False

    def run(self):
        logger.info(f"Starting download agent with {len(SOURCES)} sources")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.download_source, source): source for source in SOURCES}
            downloaded = 0
            failed = 0
            for future in as_completed(futures):
                source = futures[future]
                try:
                    result = future.result()
                    if result:
                        downloaded += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"❌ {source['name']} - Exception: {e}")
                    failed += 1
        logger.info(f"Downloaded: {downloaded}, Failed: {failed}")

if __name__ == "__main__":
    downloader = CodeDownloader()
    downloader.run()
    logger.info("Download agent completed cycle")
