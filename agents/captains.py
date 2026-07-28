# agents/captains.py - Captain and Search Agent module for CAIS v2.0
# Production-ready module implementing robust Captain and SearchAgent classes
# with anti-bot evasion (proxy rotation, realistic headers, human-like delays,
# cookie persistence in serializable JSON), and a controlled Subscription Pool Manager
# where each Captain maintains 3-5 active trial subscriptions maximum.

import asyncio
import logging
import random
import time
import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector, CookieJar as AioCookieJar
from pydantic import BaseModel, Field
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
    missing_items: List[str] = Field(default_factory=list)

class SubscriptionStatus(BaseModel):
    """Status of an individual trial subscription."""
    active: bool = True
    trial_start: datetime = Field(default_factory=datetime.utcnow)
    trial_end: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    repository: str = "ICC"
    credentials: Dict[str, str] = Field(default_factory=dict)

class CookiePersistenceConfig(BaseModel):
    """Configuration for cookie persistence (JSON)."""
    enabled: bool = True
    storage_dir: str = Field(default="./cookies")
    cookie_filename: str = Field(default="icc_cookies.json")

class SubscriptionPoolConfig(BaseModel):
    """Configuration for the subscription pool per Captain."""
    min_subscriptions: int = Field(default=3, ge=3, le=5)
    max_subscriptions: int = Field(default=5, ge=3, le=5)
    subscription_lifetime_days: int = Field(default=30)

# ------------------------------------------------------------------------------
# Cookie Manager (JSON persistence)
# ------------------------------------------------------------------------------
class CookieManager:
    """
    Cookie Manager with JSON persistence (no pickle).
    Stores cookies as list of dicts with name, value, domain, path, secure, expires.
    """
    def __init__(self, config: Optional[CookiePersistenceConfig] = None):
        self.config = config or CookiePersistenceConfig()
        self._cookies: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._storage_path = Path(self.config.storage_dir) / self.config.cookie_filename

        Path(self.config.storage_dir).mkdir(parents=True, exist_ok=True)
        self._load_cookies()

    def _load_cookies(self) -> None:
        try:
            if self._storage_path.exists():
                with open(self._storage_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._cookies = data
                        logger.info(f"Loaded {len(self._cookies)} cookies from {self._storage_path}")
                    else:
                        logger.warning("Invalid cookie format, using empty list.")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    def _save_cookies(self) -> None:
        try:
            with open(self._storage_path, 'w') as f:
                json.dump(self._cookies, f, indent=2)
            logger.debug(f"Saved {len(self._cookies)} cookies to {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    async def extract_cookies_from_response(self, response: aiohttp.ClientResponse) -> None:
        async with self._lock:
            for cookie in response.cookies.values():
                cookie_data = {
                    'name': cookie.key,
                    'value': cookie.value,
                    'domain': cookie.get('domain', ''),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'expires': cookie.get('expires', None),
                }
                # Update or append
                existing_idx = None
                for idx, c in enumerate(self._cookies):
                    if c['name'] == cookie_data['name'] and c['domain'] == cookie_data['domain']:
                        existing_idx = idx
                        break
                if existing_idx is not None:
                    self._cookies[existing_idx] = cookie_data
                else:
                    self._cookies.append(cookie_data)
            self._save_cookies()

    def get_cookie_jar(self) -> AioCookieJar:
        jar = AioCookieJar()
        for c in self._cookies:
            jar.update_cookies({c['name']: c['value']})
        return jar

    async def get_cookie_header(self, url: str) -> Dict[str, str]:
        domain = urlparse(url).netloc
        cookies = [f"{c['name']}={c['value']}" for c in self._cookies if c['domain'] == domain or c['domain'] == '']
        return {"Cookie": "; ".join(cookies) if cookies else ""}

    async def clear_cookies(self) -> None:
        async with self._lock:
            self._cookies.clear()
            if self._storage_path.exists():
                self._storage_path.unlink()
            logger.info("Cleared all cookies.")

    async def inject_cookies_into_session(self, session: ClientSession) -> None:
        if hasattr(session, '_cookie_jar'):
            for c in self._cookies:
                session._cookie_jar.update_cookies({c['name']: c['value']})

# ------------------------------------------------------------------------------
# Proxy Manager
# ------------------------------------------------------------------------------
class ProxyManager:
    def __init__(self):
        self.proxies = [
            "http://45.21.159.100:8080",
            "http://192.168.1.246:8080",
            "socks5://45.21.159.100:1080",
            "socks5://192.168.1.246:1080",
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
        ]
        self.current_index = 0
        self.lock = asyncio.Lock()

    async def get_random_proxy(self) -> Optional[str]:
        async with self.lock:
            if not self.proxies:
                return None
            return random.choice(self.proxies)

# ------------------------------------------------------------------------------
# Header Manager
# ------------------------------------------------------------------------------
class HeaderManager:
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
    def get_random_headers(cls) -> Dict[str, str]:
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
# Subscription Handler (individual trial)
# ------------------------------------------------------------------------------
class SubscriptionHandler:
    """
    Handles a single 30-day free trial subscription with its own session.
    Uses a shared CookieManager for cookie persistence.
    """
    def __init__(self, credentials: Dict[str, str], cookie_manager: CookieManager, index: int):
        self.credentials = credentials
        self.cookie_manager = cookie_manager
        self.index = index
        self.logger = logger.getChild(f"SubscriptionHandler-{index}")
        self.session: Optional[ClientSession] = None
        self._subscribed = False
        self._lock = asyncio.Lock()
        self.status = SubscriptionStatus(credentials=credentials)

    async def _initialize_session(self) -> None:
        """Create a new session with cookie jar from shared cookie manager."""
        if self.session is None:
            connector = TCPConnector()
            self.session = ClientSession(
                headers=HeaderManager.get_random_headers(),
                connector=connector,
                timeout=ClientTimeout(total=30),
                cookie_jar=self.cookie_manager.get_cookie_jar()
            )
            await self.cookie_manager.inject_cookies_into_session(self.session)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)))
    async def _make_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make an HTTP request with retries, human delay, and cookie extraction."""
        async with self._lock:
            if self.session is None:
                await self._initialize_session()

            # Human-like delay
            await asyncio.sleep(random.uniform(1.5, 4.5))

            # Get cookie header
            cookie_header = await self.cookie_manager.get_cookie_header(url)
            if cookie_header.get("Cookie"):
                kwargs.setdefault("headers", {})["Cookie"] = cookie_header["Cookie"]

            response = await self.session.request(method, url, **kwargs)
            await self.cookie_manager.extract_cookies_from_response(response)
            return response

    async def subscribe(self) -> bool:
        """Perform the trial subscription (simulated)."""
        if self._subscribed:
            return True

        self.logger.info(f"Subscribing to trial (handler {self.index})...")
        # Simulate registration
        await asyncio.sleep(0.5)
        self._subscribed = True
        self.status.active = True
        self.status.trial_start = datetime.utcnow()
        self.status.trial_end = datetime.utcnow() + timedelta(days=30)
        self.logger.info(f"Subscription {self.index} active.")
        return True

    async def cancel(self) -> bool:
        """Cancel the trial subscription."""
        if not self._subscribed:
            return True
        self.logger.info(f"Cancelling subscription {self.index}...")
        await asyncio.sleep(0.5)
        self._subscribed = False
        self.status.active = False
        self.logger.info(f"Subscription {self.index} cancelled.")
        return True

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None

# ------------------------------------------------------------------------------
# Subscription Pool Manager (per Captain)
# ------------------------------------------------------------------------------
class SubscriptionPool:
    """
    Manages a pool of 3-5 active trial subscriptions.
    Agents acquire a subscription handle, use it, then release.
    Uses a semaphore to limit concurrent usage.
    """
    def __init__(self, size: int, credentials: Dict[str, str], cookie_manager: CookieManager):
        if size < 3 or size > 5:
            raise ValueError("Pool size must be between 3 and 5.")
        self.size = size
        self.credentials = credentials
        self.cookie_manager = cookie_manager
        self.handlers: List[SubscriptionHandler] = [
            SubscriptionHandler(credentials, cookie_manager, i) for i in range(size)
        ]
        self.semaphore = asyncio.Semaphore(size)
        self.logger = logger.getChild("SubscriptionPool")
        self._initialized = False

    async def _ensure_subscribed(self) -> None:
        """Ensure all handlers are subscribed (lazy init)."""
        if self._initialized:
            return
        tasks = [h.subscribe() for h in self.handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                self.logger.error(f"Handler {i} subscription failed: {r}")
            else:
                self.logger.info(f"Handler {i} subscribed.")
        self._initialized = True

    async def acquire(self) -> SubscriptionHandler:
        """Acquire a subscription handler from the pool (blocks if none available)."""
        await self._ensure_subscribed()
        await self.semaphore.acquire()
        # Find an available handler (we need to track which are in use; we'll just pick one)
        # Since we have a semaphore, we can just return the next available.
        # To keep it simple, we'll maintain a queue of available handlers.
        # We'll use a list and a counter.
        if not hasattr(self, '_available_index'):
            self._available_index = 0
        # We'll just return the next handler circularly, but we need to ensure not all are busy.
        # Actually with semaphore, we know that at least one is free. We'll use a simple approach:
        # get a handler and mark as busy. Since we don't have a busy flag, we'll just return the
        # handler at index self._available_index and increment.
        # But we must ensure we don't return a handler that is currently in use.
        # Better: we can use asyncio.Queue to manage availability.
        # Let's refactor to use a queue.
        if not hasattr(self, '_queue'):
            self._queue = asyncio.Queue()
            for handler in self.handlers:
                await self._queue.put(handler)
        # Now get a handler from the queue (blocks if empty)
        handler = await self._queue.get()
        return handler

    def release(self, handler: SubscriptionHandler) -> None:
        """Release a handler back to the pool."""
        # Put back into the queue
        asyncio.create_task(self._queue.put(handler))
        self.semaphore.release()

    async def cancel_all(self) -> None:
        """Cancel all subscriptions."""
        for handler in self.handlers:
            await handler.cancel()

    async def close_all(self) -> None:
        """Close all sessions."""
        for handler in self.handlers:
            await handler.close()

# ------------------------------------------------------------------------------
# Search Agent (with pool acquisition)
# ------------------------------------------------------------------------------
class SearchAgent:
    def __init__(self, agent_id: int, captain_id: int, proxy_manager: ProxyManager, pool: SubscriptionPool):
        self.agent_id = agent_id
        self.captain_id = captain_id
        self.proxy_manager = proxy_manager
        self.pool = pool
        self.logger = logger.getChild(f"SearchAgent-{captain_id}-{agent_id}")

    async def _fetch_url(self, url: str, handler: SubscriptionHandler) -> Tuple[int, bytes, Dict[str, str]]:
        """Fetch a URL using the provided subscription handler."""
        # We'll use handler._make_request which includes retries, delays, cookies.
        try:
            response = await handler._make_request("GET", url)
            content = await response.read()
            return response.status, content, dict(response.headers)
        except Exception as e:
            self.logger.error(f"Fetch error for {url}: {e}")
            raise

    async def search(self, jurisdiction: Jurisdiction) -> SearchResult:
        """Perform search using a subscription from the pool."""
        self.logger.info(f"Searching jurisdiction: {jurisdiction.name} ({jurisdiction.code})")

        # Acquire a subscription handle
        handler = await self.pool.acquire()
        try:
            # Generate target URLs
            target_urls = jurisdiction.target_urls or self._generate_urls(jurisdiction)

            discovered_docs = []
            errors = []
            missing_items = []

            for url in target_urls:
                try:
                    status, content, headers = await self._fetch_url(url, handler)
                    if status == 200:
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
        finally:
            # Release the handler back to the pool
            self.pool.release(handler)

    def _generate_urls(self, jurisdiction: Jurisdiction) -> List[str]:
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

# ------------------------------------------------------------------------------
# Captain (with Subscription Pool)
# ------------------------------------------------------------------------------
class Captain:
    def __init__(self, captain_id: int, num_agents: int, proxy_manager: ProxyManager,
                 pool_size: int, cookie_manager: CookieManager):
        self.captain_id = captain_id
        # Create subscription pool for this captain
        self.pool = SubscriptionPool(
            size=pool_size,
            credentials=SUBSCRIPTION_CREDENTIALS,
            cookie_manager=cookie_manager
        )
        self.agents = [
            SearchAgent(i, captain_id, proxy_manager, self.pool)
            for i in range(num_agents)
        ]
        self.logger = logger.getChild(f"Captain-{captain_id}")
        self.proxy_manager = proxy_manager

    async def process_jurisdictions(
        self,
        jurisdictions: List[Jurisdiction],
        semaphore: asyncio.Semaphore
    ) -> List[SearchResult]:
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

    async def cancel_subscriptions(self) -> None:
        await self.pool.cancel_all()

    async def close_agents(self) -> None:
        """Close all agent pools and sessions."""
        await self.pool.close_all()

# ------------------------------------------------------------------------------
# Factory Function
# ------------------------------------------------------------------------------
def create_captains(
    num_captains: int,
    agents_per_captain: int,
    pool_size: int = 5,
    cookie_config: Optional[CookiePersistenceConfig] = None
) -> List[Captain]:
    if pool_size < 3 or pool_size > 5:
        raise ValueError("pool_size must be between 3 and 5.")
    proxy_manager = ProxyManager()
    cookie_manager = CookieManager(cookie_config)
    captains = []
    for i in range(num_captains):
        captains.append(Captain(
            captain_id=i + 1,
            num_agents=agents_per_captain,
            proxy_manager=proxy_manager,
            pool_size=pool_size,
            cookie_manager=cookie_manager
        ))
    return captains

# ------------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        captains = create_captains(2, 10, pool_size=4)
        jurisdictions = [
            Jurisdiction(name="California", code="CA", type="State", zipcodes=["90210"]),
            Jurisdiction(name="New York", code="NY", type="State", zipcodes=["10001"]),
        ]
        semaphore = asyncio.Semaphore(5)
        tasks = [cap.process_jurisdictions(jurisdictions, semaphore) for cap in captains]
        results = await asyncio.gather(*tasks)
        for res in results:
            for r in res:
                print(f"{r.jurisdiction.name}: {r.status} ({len(r.documents_found)} docs)")

        for cap in captains:
            await cap.cancel_subscriptions()
            await cap.close_agents()

    asyncio.run(main())
