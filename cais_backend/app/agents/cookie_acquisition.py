#!/usr/bin/env python3
"""
cookie_acquisition.py - Acquires ICC session cookies using Playwright.
"""

import os, json, time, logging
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COOKIES_FILE = "/tmp/selenium_cookies.json"
EMAIL = os.environ.get("ICC_EMAIL", "caiscodecompliance@gmail.com")
PASSWORD = os.environ.get("ICC_PASSWORD", "051664Wmr!$")

def acquire():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(user_agent="Mozilla/5.0")
        page = context.new_page()
        page.goto("https://codes.iccsafe.org/", timeout=60000)
        page.wait_for_load_state("networkidle")
        login = page.query_selector("a:has-text('Log In')")
        if login:
            login.click()
            page.wait_for_load_state("networkidle")
        page.fill("input[type='email']", EMAIL)
        page.fill("input[type='password']", PASSWORD)
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        cookies = context.cookies()
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f, indent=2)
        logger.info(f"Saved {len(cookies)} cookies")
        browser.close()

if __name__ == "__main__":
    acquire()
