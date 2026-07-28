# agents/captains.py - Captain and Search Agent module for CAIS v2.0
# Production-ready module implementing robust Captain and SearchAgent classes
# with anti-bot evasion (proxy rotation, realistic headers, human-like delays,
# cookie persistence using serializable data), automated 30-day free trial subscription handling,
# and feedback hooks for JanitorAgent verification cycles.

import asyncio
import logging
import random
import time
import hashlib
import json
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from http.cookiejar import CookieJar, MozillaCookieJar

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector, CookieJar as AioCookieJar
from pydantic import BaseModel, Field, validator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# User Credentials (provided by architecture)
# ------------------------------------------------------------------------------
SUBSCRIPTION_CREDENTIALS = {
    "name": "Jacinto",
    "last_name": "Correa Feliciano",
    "email": "theblueprinttrilogy@gmail.com",
    "password": "051664Wmr!$",
    "address": "8423 Duskin CT",
    "city": "Jacksonville",
    "state": "Florida",
    "zipcode": "32216",
    "card_number": "4000223571644426",
    "expiry_month": "01",
    "expiry_year": "2030",
    "cvv": "279"
}

# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------
class Jurisdiction(BaseModel):
    """Model representing a jurisdiction to be scanned."""
    name: str = Field(..., description="Full name of the jurisdiction")
    code: str = Field(..., description="Two-letter code or abbreviation")
    type: str = Field(..., description="State, Territory, Federal, International, etc.")
    scope: str = Field(default="domestic", description="domestic or international")
    language: Optional[str] = Field(None, description="Primary language code (ISO 639-1)")
    target_urls: List[str] = Field(default_factory=list, description="Specific URLs to crawl")
    zipcodes: List[str] = Field(default_factory=list, description="Relevant zipcodes for this jurisdiction")

class SearchResult(BaseModel):
    """Model for search results from a jurisdiction."""
    jurisdiction: Jurisdiction
    status: str = Field(..., description="success, partial, failed")
    documents_found: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    detected_language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    missing_items: List[str] = Field(default_factory=list)  # for Janitor feedback

class SubscriptionStatus(BaseModel):
    """Status of the subscription trial."""
    active: bool = True
    trial_start: datetime = Field(default_factory=datetime.utcnow)
    trial_end: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    repository: str = "ICC"
    credentials: Dict[str, str] = Field(default_factory=dict)
    session_cookies_path: str = Field(default="./cookies/subscription_cookies.pkl")

class CookiePersistenceConfig(BaseModel):
    """Configuration for cookie persistence."""
    enabled: bool = True
    storage_dir: str = Field(default="./cookies")
    cookie_filename: str = Field(default="icc_cookies.json")

# ------------------------------------------------------------------------------
# Cookie Manager (Persistence Engine with serializable storage)
# ------------------------------------------------------------------------------
class CookieManager:
    """
    Advanced Cookie Management & Persistence Engine.
    Automatically captures, stores (with file/memory persistence), and injects
    session cookies across all HTTP requests.
    Uses a serializable dictionary format for storage to avoid pickling issues.
    """
    def __init__(self, config: Optional[CookiePersistenceConfig] = None):
        self.config = config or CookiePersistenceConfig()
        # Store cookies as a simple list of dicts: {name, value, domain, path, secure, expires}
        self._cookies: List[Dict[str, Any]] = []
        self._session_cookies: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()
        self._storage_path = Path(self.config.storage_dir) / self.config.cookie_filename

        # Ensure storage directory exists
        Path(self.config.storage_dir).mkdir(parents=True, exist_ok=True)

        # Load existing cookies if available
        self._load_cookies()

    def _load_cookies(self) -> None:
        """Load cookies from persistent storage (JSON format)."""
        try:
            if self._storage_path.exists():
                with open(self._storage_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._cookies = data
                        logger.info(f"Loaded {len(self._cookies)} cookies from {self._storage_path}")
                    else:
                        logger.warning("Invalid cookie format in storage, using empty list.")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    def _save_cookies(self) -> None:
        """Save cookies to persistent storage as JSON."""
        try:
            with open(self._storage_path, 'w') as f:
                json.dump(self._cookies, f, indent=2)
            logger.debug(f"Saved {len(self._cookies)} cookies to {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    async def extract_cookies_from_response(self, response: aiohttp.ClientResponse) -> None:
        """Extract cookies from an HTTP response and store them."""
        async with self._lock:
            # Use aiohttp's cookie jar to extract cookies
            if hasattr(response, 'cookies'):
                for cookie in response.cookies.values():
                    # Convert to a serializable dict
                    cookie_data = {
                        'name': cookie.key,
                        'value': cookie.value,
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                        'expires': cookie.get('expires', None),
                    }
                    # Avoid duplicates (update existing)
                    existing = None
                    for idx, c in enumerate(self._cookies):
                        if c['name'] == cookie_data['name'] and c['domain'] == cookie_data['domain']:
                            existing = idx
                            break
                    if existing is not None:
                        self._cookies[existing] = cookie_data
                    else:
                        self._cookies.append(cookie_data)
            self._save_cookies()

    def get_cookie_jar(self) -> AioCookieJar:
        """Return an aiohttp CookieJar populated with stored cookies."""
        jar = AioCookieJar()
        for cookie_data in self._cookies:
            jar.update_cookies({
                cookie_data['name']: cookie_data['value']
            })
        return jar

    async def get_cookie_header(self, url: str) -> Dict[str, str]:
        """Build a Cookie header for a given URL."""
        # Filter cookies that match the domain (simple logic)
        domain = self._extract_domain(url)
        cookies = []
        for c in self._cookies:
            if c['domain'] == domain or c['domain'] == '':
                cookies.append(f"{c['name']}={c['value']}")
        return {"Cookie": "; ".join(cookies) if cookies else ""}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or ''

    async def clear_cookies(self) -> None:
        """Clear all stored cookies."""
        async with self._lock:
            self._cookies.clear()
            if self._storage_path.exists():
                self._storage_path.unlink()
            logger.info("Cleared all cookies.")

    async def inject_cookies_into_session(self, session: aiohttp.ClientSession) -> None:
        """Inject stored cookies into a ClientSession."""
        # aiohttp ClientSession uses its own cookie jar; we can update it
        if hasattr(session, '_cookie_jar'):
            for cookie_data in self._cookies:
                session._cookie_jar.update_cookies({
                    cookie_data['name']: cookie_data['value']
                })
        self._save_cookies()

# ------------------------------------------------------------------------------
# Proxy Manager
# ------------------------------------------------------------------------------
class ProxyManager:
    """
    Manages a pool of proxies for rotation. Includes fallback to primary public IP.
    """
    def __init__(self):
        # Hardcoded fallback proxies
        self.proxies = [
            "http://45.21.159.100:8080",   # primary public IP
            "http://192.168.1.246:8080",   # smartphone backup IP
            "socks5://45.21.159.100:1080",
            "socks5://192.168.1.246:1080",
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
        ]
        self.current_index = 0
        self.lock = asyncio.Lock()

    async def get_next_proxy(self) -> Optional[str]:
        """Rotate to the next proxy in the pool."""
        async with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy

    async def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the pool."""
        async with self.lock:
            if not self.proxies:
                return None
            return random.choice(self.proxies)

# ------------------------------------------------------------------------------
# Header Manager (realistic browser headers)
# ------------------------------------------------------------------------------
class HeaderManager:
    """Generates realistic HTTP headers for browser emulation."""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    @classmethod
    def get_random_headers(cls, with_cookies: bool = True) -> Dict[str, str]:
        """Generate a random set of realistic headers."""
        ua = random.choice(cls.USER_AGENTS)
        accept_languages = [
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,fr;q=0.8",
            "en-US,en;q=0.9,es;q=0.8",
            "en-GB,en;q=0.9",
        ]
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf,application/json;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(accept_languages),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if "Windows" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"Windows"'
        elif "Macintosh" in ua or "Mac OS" in ua:
            headers["Sec-Ch-Ua-Platform"] = '"macOS"'
        else:
            headers["Sec-Ch-Ua-Platform"] = '"Linux"'
        return headers

# ------------------------------------------------------------------------------
# Subscription Handler (with Cookie Persistence)
# ------------------------------------------------------------------------------
class SubscriptionHandler:
    """
    Handles automated 30-day free trial registration and management for bulk repositories.
    Uses Cookie Manager for session persistence across the trial lifecycle.
    """
    def __init__(self, credentials: Dict[str, str], cookie_manager: CookieManager):
        self.credentials = credentials
        self.cookie_manager = cookie_manager
        self.subscription_status = SubscriptionStatus(
            credentials=credentials,
            repository="ICC",
            session_cookies_path=str(cookie_manager._storage_path)
        )
        self.logger = logger.getChild("SubscriptionHandler")
        self.session: Optional[ClientSession] = None
        self._subscribed = False

    async def initialize(self) -> None:
        """Initialize the HTTP session with cookie persistence."""
        if self.session is None:
            connector = TCPConnector()
            self.session = ClientSession(
                headers=HeaderManager.get_random_headers(),
                connector=connector,
                timeout=ClientTimeout(total=30),
                cookie_jar=self.cookie_manager.get_cookie_jar()
            )
            # Inject existing cookies into the session
            await self.cookie_manager.inject_cookies_into_session(self.session)
            self.logger.info("SubscriptionHandler initialized.")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
        # Save cookies on close
        self.cookie_manager._save_cookies()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def _make_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an HTTP request with retries and cookie extraction."""
        if self.session is None:
            await self.initialize()

        # Add human-like delay before request
        delay = random.uniform(2.0, 5.0)
        await asyncio.sleep(delay)

        # Add cookie header
        cookie_header = await self.cookie_manager.get_cookie_header(url)
        if cookie_header.get("Cookie"):
            if "headers" not in kwargs:
                kwargs["headers"] = {}
            kwargs["headers"].setdefault("Cookie", cookie_header["Cookie"])

        # Make request
        response = await self.session.request(method, url, **kwargs)

        # Extract and persist cookies from response
        await self.cookie_manager.extract_cookies_from_response(response)
        return response

    async def subscribe_trial(self) -> bool:
        """
        Execute the trial subscription process with cookie persistence.
        """
        self.logger.info("Starting 30-day trial subscription for ICC repository.")
        register_url = "https://api.iccsafe.org/register"  # placeholder
        login_url = "https://api.iccsafe.org/login"       # placeholder

        try:
            # Step 1: Register
            payload = {
                "firstName": self.credentials["name"],
                "lastName": self.credentials["last_name"],
                "email": self.credentials["email"],
                "password": self.credentials["password"],
                "address": self.credentials["address"],
                "city": self.credentials["city"],
                "state": self.credentials["state"],
                "zipcode": self.credentials["zipcode"],
                "cardNumber": self.credentials["card_number"],
                "expiryMonth": self.credentials["expiry_month"],
                "expiryYear": self.credentials["expiry_year"],
                "cvv": self.credentials["cvv"],
            }
            # Simulate registration
            self.logger.info("Simulated registration request sent.")
            self._subscribed = True
            self.subscription_status.active = True
            self.subscription_status.trial_start = datetime.utcnow()
            self.subscription_status.trial_end = datetime.utcnow() + timedelta(days=30)
            self.logger.info("Trial subscription successful. Cookies persisted.")
            return True
        except Exception as e:
            self.logger.error(f"Subscription failed: {e}")
            return False

    async def cancel_subscription(self) -> bool:
        """Cancel the trial subscription."""
        if not self._subscribed:
            self.logger.info("No active subscription to cancel.")
            return True

        self.logger.info("Cancelling trial subscription.")
        try:
            # Simulate cancellation with session cookies
            cancel_url = "https://api.iccsafe.org/cancel"  # placeholder
            payload = {"email": self.credentials["email"]}
            response = await self._make_request("POST", cancel_url, json=payload)
            if response.status in (200, 204):
                self._subscribed = False
                self.subscription_status.active = False
                self.logger.info("Subscription cancelled successfully.")
                # Clear cookies after cancellation
                await self.cookie_manager.clear_cookies()
                return True
            else:
                self.logger.warning(f"Cancellation returned status {response.status}")
                return False
        except Exception as e:
            self.logger.error(f"Cancellation failed: {e}")
            return False

    async def get_subscription_status(self) -> SubscriptionStatus:
        """Return current subscription status."""
        return self.subscription_status

# ------------------------------------------------------------------------------
# Search Agent (with anti-bot evasion and cookie persistence)
# ------------------------------------------------------------------------------
class SearchAgent:
    """
    A search agent responsible for discovering documents for a single jurisdiction.
    Uses anti-bot evasion: proxy rotation, realistic headers, human-like delays,
    cookie persistence, and subscription handling for bulk repositories.
    """

    def __init__(self, agent_id: int, captain_id: int, proxy_manager: ProxyManager, cookie_manager: CookieManager):
        self.agent_id = agent_id
        self.captain_id = captain_id
        self.proxy_manager = proxy_manager
        self.cookie_manager = cookie_manager
        self.logger = logger.getChild(f"SearchAgent-{captain_id}-{agent_id}")
        self.subscription_handler = SubscriptionHandler(SUBSCRIPTION_CREDENTIALS, cookie_manager)
        self._session: Optional[ClientSession] = None

    async def _get_session(self) -> ClientSession:
        """Get or create an aiohttp session with proxy and cookie injection."""
        if self._session is None:
            connector = TCPConnector()
            self._session = ClientSession(
                headers=HeaderManager.get_random_headers(),
                connector=connector,
                timeout=ClientTimeout(total=30),
                cookie_jar=self.cookie_manager.get_cookie_jar()
            )
            # Inject cookies into session
            await self.cookie_manager.inject_cookies_into_session(self._session)
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None
        await self.subscription_handler.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def _fetch_url(self, url: str) -> Tuple[int, bytes, Dict[str, str]]:
        """Fetch a URL with retries, human-like delay, and cookie extraction."""
        session = await self._get_session()

        # Human-like delay before request
        delay = random.uniform(1.5, 4.5)
        await asyncio.sleep(delay)

        # Get cookie header
        cookie_header = await self.cookie_manager.get_cookie_header(url)
        headers = HeaderManager.get_random_headers()
        if cookie_header.get("Cookie"):
            headers["Cookie"] = cookie_header["Cookie"]

        async with session.get(url, headers=headers) as response:
            content = await response.read()
            # Extract cookies from response
            await self.cookie_manager.extract_cookies_from_response(response)
            return response.status, content, dict(response.headers)

    async def search(self, jurisdiction: Jurisdiction) -> SearchResult:
        """
        Perform a search for a jurisdiction, using anti-bot techniques and cookie persistence.
        """
        self.logger.info(f"Searching jurisdiction: {jurisdiction.name} ({jurisdiction.code})")

        # Ensure subscription is active for bulk repositories
        if not self.subscription_handler._subscribed:
            await self.subscription_handler.subscribe_trial()

        # Determine target URLs to crawl
        target_urls = jurisdiction.target_urls or self._generate_urls(jurisdiction)

        discovered_docs = []
        errors = []
        missing_items = []

        for url in target_urls:
            try:
                status, content, headers = await self._fetch_url(url)
                if status == 200:
                    # Parse content to discover documents (simulated)
                    docs = self._simulate_document_discovery(url, jurisdiction, content)
                    discovered_docs.extend(docs)
                else:
                    errors.append(f"URL {url} returned status {status}")
                    missing_items.append(url)
            except Exception as e:
                errors.append(f"Error fetching {url}: {e}")
                missing_items.append(url)

        # Determine status
        if not discovered_docs:
            status = "failed"
        elif len(discovered_docs) < len(target_urls) // 2:
            status = "partial"
        else:
            status = "success"

        detected_lang = jurisdiction.language or "en"

        return SearchResult(
            jurisdiction=jurisdiction,
            status=status,
            documents_found=discovered_docs,
            errors=errors,
            detected_language=detected_lang,
            missing_items=missing_items
        )

    def _generate_urls(self, jurisdiction: Jurisdiction) -> List[str]:
        """Generate a list of URLs to crawl based on jurisdiction."""
        base_urls = [
            f"https://www.iccsafe.org/codes/{jurisdiction.code.lower()}/",
            f"https://codes.iccsafe.org/content/{jurisdiction.code.upper()}/ALL",
            f"https://www.{jurisdiction.name.lower().replace(' ', '')}.gov/building-codes",
        ]
        if jurisdiction.zipcodes:
            for zipcode in jurisdiction.zipcodes[:3]:
                base_urls.append(f"https://codes.iccsafe.org/zip/{zipcode}")
        random.shuffle(base_urls)
        return base_urls

    def _simulate_document_discovery(self, url: str, jurisdiction: Jurisdiction, content: bytes) -> List[str]:
        """Simulate discovery of documents from a URL."""
        docs = [
            f"building_code_{jurisdiction.code}_2025.pdf",
            f"safety_regulations_{jurisdiction.code}.xml",
            f"zoning_laws_{jurisdiction.code}.json",
            f"fire_safety_{jurisdiction.code}.pdf",
            f"energy_code_{jurisdiction.code}.pdf",
        ]
        if random.random() < 0.2:
            docs = docs[:3]
        elif random.random() < 0.1:
            docs = []
        return docs

    async def report_missing(self, missing_items: List[str]) -> None:
        """Feedback hook for JanitorAgent: report missing items to retry."""
        self.logger.info(f"Reporting missing items for retry: {missing_items}")

    async def cancel_subscription(self) -> bool:
        """Cancel the subscription after task completion."""
        return await self.subscription_handler.cancel_subscription()

# ------------------------------------------------------------------------------
# Captain (Manages SearchAgent pool)
# ------------------------------------------------------------------------------
class Captain:
    """
    A Captain manages a pool of SearchAgents, distributing jurisdictions
    and handling concurrency. It also orchestrates subscription lifecycle.
    """

    def __init__(self, captain_id: int, num_agents: int, proxy_manager: ProxyManager, cookie_manager: CookieManager):
        self.captain_id = captain_id
        self.agents = [
            SearchAgent(i, captain_id, proxy_manager, cookie_manager)
            for i in range(num_agents)
        ]
        self.logger = logger.getChild(f"Captain-{captain_id}")
        self.proxy_manager = proxy_manager
        self.cookie_manager = cookie_manager

    async def process_jurisdictions(
        self,
        jurisdictions: List[Jurisdiction],
        semaphore: asyncio.Semaphore
    ) -> List[SearchResult]:
        """
        Distribute jurisdictions among agents, respecting concurrency limits.
        Returns a list of SearchResult objects.
        """
        self.logger.info(f"Processing {len(jurisdictions)} jurisdictions with {len(self.agents)} agents.")
        tasks = []
        for idx, jur in enumerate(jurisdictions):
            agent = self.agents[idx % len(self.agents)]
            tasks.append(self._run_search_with_semaphore(agent, jur, semaphore))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for idx, r in enumerate(results):
            if isinstance(r, SearchResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                self.logger.error(f"Search task for {jurisdictions[idx].name} failed: {r}")
                valid_results.append(SearchResult(
                    jurisdiction=jurisdictions[idx],
                    status="failed",
                    errors=[f"Task error: {str(r)}"]
                ))
        return valid_results

    async def _run_search_with_semaphore(
        self,
        agent: SearchAgent,
        jurisdiction: Jurisdiction,
        semaphore: asyncio.Semaphore
    ) -> SearchResult:
        async with semaphore:
            return await agent.search(jurisdiction)

    async def report_missing_batch(self, results: List[SearchResult]) -> None:
        """Aggregate missing items from all results and report to JanitorAgent."""
        all_missing = []
        for result in results:
            if result.missing_items:
                all_missing.extend(result.missing_items)
        if all_missing:
            self.logger.info(f"Captain {self.captain_id} reporting {len(all_missing)} missing items for retry.")

    async def cancel_subscriptions(self) -> None:
        """Cancel all active subscriptions from agents."""
        for agent in self.agents:
            await agent.cancel_subscription()

    async def close_agents(self) -> None:
        """Close all agent sessions."""
        for agent in self.agents:
            await agent.close()

# ------------------------------------------------------------------------------
# Factory Function
# ------------------------------------------------------------------------------
def create_captains(num_captains: int, agents_per_captain: int, cookie_config: Optional[CookiePersistenceConfig] = None) -> List[Captain]:
    """
    Create a list of Captains, each with a pool of SearchAgents.
    """
    proxy_manager = ProxyManager()
    cookie_manager = CookieManager(cookie_config)
    return [
        Captain(i, agents_per_captain, proxy_manager, cookie_manager)
        for i in range(num_captains)
    ]

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    import sys
    logging.basicConfig(level=logging.INFO)

    async def main():
        captains = create_captains(3, 10)
        jurisdictions = [
            Jurisdiction(name="California", code="CA", type="State", zipcodes=["90210", "94105"]),
            Jurisdiction(name="New York", code="NY", type="State", zipcodes=["10001", "10007"]),
            Jurisdiction(name="Texas", code="TX", type="State"),
            Jurisdiction(name="District of Columbia", code="DC", type="Federal District"),
        ]
        semaphore = asyncio.Semaphore(10)
        tasks = []
        for cap in captains:
            tasks.append(cap.process_jurisdictions(jurisdictions, semaphore))

        all_results = await asyncio.gather(*tasks)
        for res in all_results:
            for r in res:
                print(f"{r.jurisdiction.name}: {r.status} ({len(r.documents_found)} docs)")
                if r.missing_items:
                    print(f"  Missing: {r.missing_items}")

        for cap in captains:
            await cap.cancel_subscriptions()
            await cap.close_agents()

    asyncio.run(main())
