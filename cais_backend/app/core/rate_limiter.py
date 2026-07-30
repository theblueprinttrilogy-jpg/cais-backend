"""
Rate Limiter Core - API Rate Limiting

This module provides rate limiting for API endpoints.
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException


class RateLimiter:
    """
    Rate limiter for API endpoints.

    Features:
    - Per-IP rate limiting
    - Per-user rate limiting
    - Configurable limits per endpoint
    - Sliding window algorithm
    """

    def __init__(self):
        self._ip_requests: Dict[str, list] = defaultdict(list)
        self._user_requests: Dict[str, list] = defaultdict(list)

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        request_type: str = "ip"
    ) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded.

        Args:
            key: Identifier (IP or user ID)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            request_type: "ip" or "user"

        Returns:
            Tuple[bool, int]: (allowed, remaining)
        """
        now = time.time()

        # Get requests for this key
        if request_type == "ip":
            requests = self._ip_requests[key]
        else:
            requests = self._user_requests[key]

        # Clean old requests
        requests = [t for t in requests if t > now - window_seconds]

        # Check if limit is exceeded
        if len(requests) >= limit:
            remaining = 0
            allowed = False
        else:
            remaining = limit - len(requests)
            allowed = True
            requests.append(now)

        # Update requests
        if request_type == "ip":
            self._ip_requests[key] = requests
        else:
            self._user_requests[key] = requests

        return allowed, remaining

    def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        request_type: str = "ip"
    ) -> int:
        """
        Get remaining requests for a key.

        Args:
            key: Identifier (IP or user ID)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            request_type: "ip" or "user"

        Returns:
            int: Remaining requests
        """
        now = time.time()

        if request_type == "ip":
            requests = self._ip_requests.get(key, [])
        else:
            requests = self._user_requests.get(key, [])

        # Clean old requests
        requests = [t for t in requests if t > now - window_seconds]

        remaining = max(0, limit - len(requests))
        return remaining

    def reset(self, key: str, request_type: str = "ip"):
        """
        Reset rate limit for a key.
        """
        if request_type == "ip":
            if key in self._ip_requests:
                del self._ip_requests[key]
        else:
            if key in self._user_requests:
                del self._user_requests[key]


# Default rate limiter instance
default_limiter = RateLimiter()


class RateLimitMiddleware:
    """
    Middleware for rate limiting.
    """

    def __init__(
        self,
        limiter: RateLimiter = None,
        default_limit: int = 100,
        default_window: int = 60
    ):
        self.limiter = limiter or default_limiter
        self.default_limit = default_limit
        self.default_window = default_window

    async def __call__(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        path = request.url.path

        # Determine rate limit based on path
        limit, window = self._get_limits(path)

        # Check rate limit
        allowed, remaining = self.limiter.check_rate_limit(
            client_ip, limit, window, "ip"
        )

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "0.0.0.0"

    def _get_limits(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit for a path.

        Returns:
            Tuple[int, int]: (limit, window_seconds)
        """
        # Authentication endpoints have higher limits
        if "/auth/" in path:
            return 20, 60

        # Upload endpoints have lower limits
        if "/upload/" in path:
            return 10, 300

        # Analysis endpoints
        if "/analysis/" in path:
            return 30, 60

        # Default
        return self.default_limit, self.default_window
