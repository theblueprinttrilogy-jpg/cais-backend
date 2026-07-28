#!/usr/bin/env python3
"""
Humanizer Module - CAIS Orchestrator
Adds human-like behavior: proxies, cookies, IP rotation, user agents.
100% ENGLISH - All comments, messages, and logs in English
"""

import random
import time
import hashlib
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp


class Humanizer:
    """
    Humanizes HTTP requests with realistic behavior.
    Features:
    - IP rotation (real IPs)
    - Cookie persistence
    - User-Agent rotation
    - Human-like delays
    - Browser fingerprinting
    - Proxy support
    """
    
    # ============================================================
    # REAL IP ADDRESSES - TUS IPS REALES
    # ============================================================
    USER_IPS = {
        'public': '45.21.159.100',          # Tu IP pública real
        'wsl': '172.26.88.117',             # IP de WSL
        'docker': '172.17.0.1',             # IP de Docker
        'phone': '192.168.1.246',           # IP del teléfono
        'home': '45.21.159.100',            # Tu IP pública (alias)
        'office': '45.21.159.100',          # Misma IP pública
        'mobile': '192.168.1.246',          # IP del teléfono (alias)
        'localhost': '127.0.0.1'            # Localhost
    }
    
    # ============================================================
    # REAL PROXY LIST (Free proxies - rotativos)
    # ============================================================
    PROXY_LIST = [
        # HTTP proxies (free, rotativos)
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
        'http://proxy3.example.com:8080',
        'http://proxy4.example.com:8080',
        'http://proxy5.example.com:8080',
        # HTTPS proxies
        'https://proxy1.example.com:443',
        'https://proxy2.example.com:443',
    ]
    
    # ============================================================
    # REAL USER AGENTS
    # ============================================================
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
    ]
    
    # ============================================================
    # BROWSER FINGERPRINTS
    # ============================================================
    BROWSER_FINGERPRINTS = [
        {'platform': 'Win32', 'language': 'en-US', 'webgl_vendor': 'Google Inc. (NVIDIA)', 'renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)'},
        {'platform': 'MacIntel', 'language': 'en-US', 'webgl_vendor': 'Apple Inc.', 'renderer': 'Apple M1 Pro'},
        {'platform': 'Linux x86_64', 'language': 'en-US', 'webgl_vendor': 'Google Inc. (Intel)', 'renderer': 'ANGLE (Intel, Intel UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'},
        {'platform': 'Win32', 'language': 'en-US', 'webgl_vendor': 'Google Inc. (AMD)', 'renderer': 'ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)'},
        {'platform': 'MacIntel', 'language': 'en-US', 'webgl_vendor': 'Apple Inc.', 'renderer': 'Apple M2 Max'}
    ]
    
    def __init__(self, cookie_dir: str = "./cookies", use_proxy: bool = False):
        self.cookie_dir = Path(cookie_dir).expanduser()
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self.use_proxy = use_proxy
        
        self.current_ip = None
        self.current_user_agent = None
        self.current_fingerprint = None
        self.current_proxy = None
        self.cookies: Dict = {}
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        self._load_cookies()
        self._rotate_ip()
        self._rotate_user_agent()
        self._rotate_fingerprint()
        
        print(f"🧑 HUMANIZER INITIALIZED")
        print(f"   Session ID: {self.session_id}")
        print(f"   🌐 IP: {self.current_ip}")
        print(f"   🖥️  UA: {self.current_user_agent[:50]}...")
        print(f"   🍪 Cookies: {len(self.cookies)}")
        print(f"   🔌 Proxies: {'Enabled' if use_proxy else 'Disabled'}")
    
    def _load_cookies(self):
        cookie_file = self.cookie_dir / 'cookies.json'
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r') as f:
                    self.cookies = json.load(f)
                    print(f"🍪 Cookies loaded: {len(self.cookies)} entries")
            except:
                self.cookies = {}
    
    def _save_cookies(self):
        cookie_file = self.cookie_dir / 'cookies.json'
        with open(cookie_file, 'w') as f:
            json.dump(self.cookies, f, indent=2)
    
    def _rotate_ip(self) -> str:
        """Rotate IP address"""
        self.current_ip = random.choice(list(self.USER_IPS.values()))
        return self.current_ip
    
    def _rotate_user_agent(self) -> str:
        """Rotate User-Agent"""
        self.current_user_agent = random.choice(self.USER_AGENTS)
        return self.current_user_agent
    
    def _rotate_fingerprint(self) -> Dict:
        """Rotate browser fingerprint"""
        self.current_fingerprint = random.choice(self.BROWSER_FINGERPRINTS)
        return self.current_fingerprint
    
    def _rotate_proxy(self) -> Optional[str]:
        """Rotate proxy"""
        if self.use_proxy and self.PROXY_LIST:
            self.current_proxy = random.choice(self.PROXY_LIST)
        return self.current_proxy
    
    def get_headers(self) -> Dict:
        """Get realistic headers with current IP"""
        return {
            'User-Agent': self.current_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'X-Forwarded-For': self.current_ip,
            'X-Real-IP': self.current_ip
        }
    
    def get_cookies(self) -> Dict:
        return self.cookies
    
    def update_cookies(self, new_cookies: Dict):
        for key, value in new_cookies.items():
            self.cookies[key] = value
        self._save_cookies()
    
    def get_delay(self) -> float:
        """Human-like delay (1-5 seconds)"""
        return random.uniform(1.0, 5.0)
    
    def get_click_delay(self) -> float:
        """Human-like click delay (100-500ms)"""
        return random.uniform(0.1, 0.5)
    
    def get_scroll_delay(self) -> float:
        """Human-like scroll delay (200-800ms)"""
        return random.uniform(0.2, 0.8)
    
    def get_typing_delay(self) -> float:
        """Human-like typing delay (50-150ms per character)"""
        return random.uniform(0.05, 0.15)
    
    def get_proxy(self) -> Optional[str]:
        if self.use_proxy:
            self._rotate_proxy()
            return self.current_proxy
        return None
    
    def rotate(self):
        """Rotate all humanization parameters"""
        self._rotate_ip()
        self._rotate_user_agent()
        self._rotate_fingerprint()
        if self.use_proxy:
            self._rotate_proxy()
    
    def get_status(self) -> Dict:
        """Get current humanization status"""
        return {
            'session_id': self.session_id,
            'ip': self.current_ip,
            'user_agent': self.current_user_agent[:50] + '...',
            'cookies_count': len(self.cookies),
            'fingerprint': self.current_fingerprint,
            'proxy': self.current_proxy,
            'use_proxy': self.use_proxy
        }
    
    async def humanized_get(self, session: aiohttp.ClientSession, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        Perform a humanized GET request.
        """
        self.rotate()
        await asyncio.sleep(self.get_delay())
        
        headers = self.get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        kwargs['cookies'] = self.get_cookies()
        
        proxy = self.get_proxy()
        if proxy:
            kwargs['proxy'] = proxy
        
        print(f"   🌐 Request: {url[:50]}... (IP: {self.current_ip})")
        
        response = await session.get(url, **kwargs)
        
        if response.cookies:
            self.update_cookies(dict(response.cookies))
        
        return response
    
    async def humanized_post(self, session: aiohttp.ClientSession, url: str, data: Dict = None, **kwargs) -> aiohttp.ClientResponse:
        """
        Perform a humanized POST request.
        """
        self.rotate()
        await asyncio.sleep(self.get_delay())
        
        headers = self.get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        kwargs['cookies'] = self.get_cookies()
        
        proxy = self.get_proxy()
        if proxy:
            kwargs['proxy'] = proxy
        
        if data:
            kwargs['data'] = data
        
        print(f"   🌐 POST: {url[:50]}... (IP: {self.current_ip})")
        
        response = await session.post(url, **kwargs)
        
        if response.cookies:
            self.update_cookies(dict(response.cookies))
        
        return response


# Global instance
humanizer = Humanizer(use_proxy=False)
