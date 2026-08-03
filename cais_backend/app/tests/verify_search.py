"""
app/tests/verify_search.py

Test script to verify the semantic search endpoint of the CAIS Code Compliance backend.
Sends a query to the /api/v1/search endpoint and prints the response.
Handles authentication if a token is required.
"""

import os
import sys
import json
import logging
from typing import Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default base URL (can be overridden by environment variable)
BASE_URL = os.getenv("CAIS_API_URL", "http://localhost:8080")
AUTH_ENDPOINT = f"{BASE_URL}/api/v1/auth/login"
SEARCH_ENDPOINT = f"{BASE_URL}/api/v1/search"

# Test credentials (adjust as needed for your authentication setup)
TEST_USERNAME = os.getenv("CAIS_TEST_USERNAME", "admin")
TEST_PASSWORD = os.getenv("CAIS_TEST_PASSWORD", "admin123")


def get_access_token(username: str, password: str) -> Optional[str]:
    """
    Attempt to obtain a JWT access token using the authentication endpoint.
    If authentication is not configured or fails, returns None to proceed without token.

    :param username: Username for login.
    :param password: Password for login.
    :return: Access token string or None if authentication is unavailable.
    """
    try:
        response = requests.post(
            AUTH_ENDPOINT,
            json={"username": username, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                logger.info("Successfully obtained access token.")
                return token
        logger.warning(f"Authentication failed with status {response.status_code}. Proceeding without token.")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Authentication endpoint unreachable: {e}. Proceeding without token.")
    return None


def verify_search(query: str = "fire safety", limit: int = 1) -> None:
    """
    Send a POST request to the search endpoint and log the response.

    :param query: Search query string.
    :param limit: Maximum number of results.
    """
    # Obtain token if authentication is available
    token = get_access_token(TEST_USERNAME, TEST_PASSWORD)

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"query": query, "limit": limit}

    try:
        logger.info(f"Sending search request to {SEARCH_ENDPOINT}")
        response = requests.post(
            SEARCH_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )

        # Log status and response
        logger.info(f"Status Code: {response.status_code}")
        try:
            response_json = response.json()
            logger.info("Response Body:")
            print(json.dumps(response_json, indent=2))
        except json.JSONDecodeError:
            logger.error("Response is not valid JSON.")
            logger.error(f"Raw response: {response.text}")

        # Optional: assert status code is 200 for verification
        if response.status_code != 200:
            logger.error(f"Unexpected status code: {response.status_code}")
            sys.exit(1)
        else:
            logger.info("Search endpoint verification successful.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Parse command-line arguments for flexibility
    import argparse
    parser = argparse.ArgumentParser(description="Verify CAIS search endpoint.")
    parser.add_argument("--query", default="fire safety", help="Search query")
    parser.add_argument("--limit", type=int, default=1, help="Number of results")
    args = parser.parse_args()

    verify_search(query=args.query, limit=args.limit)
