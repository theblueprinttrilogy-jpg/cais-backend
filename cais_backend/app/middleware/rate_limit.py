"""
Rate Limit Middleware - API Rate Limiting

This middleware provides rate limiting for API endpoints.
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    Features:
    - Per-IP rate limiting
    - Configurable limits per endpoint
    - Sliding window algorithm
    - Rate limit headers
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        excluded_paths: list = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self._requests: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """
        Process the request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response: Outgoing response with rate limit headers
        """
        path = request.url.path

        # Skip rate limiting for excluded paths
        if path in self.excluded_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        limit, window = self._get_limits(path)

        # Check rate limit
        allowed, remaining, reset_time = self._check_rate_limit(
            client_ip, limit, window
        )

        if not allowed:
            return Response(
                content='{"error": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(window),
                }
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

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
        Get rate limit for a specific path.

        Returns:
            Tuple[int, int]: (limit, window_seconds)
        """
        if "/auth/" in path:
            return 20, 60
        elif "/upload/" in path:
            return 10, 300
        elif "/analysis/" in path:
            return 30, 60
        elif "/admin/" in path:
            return 10, 60
        else:
            return self.default_limit, self.default_window

    def _check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Check if rate limit is exceeded.

        Returns:
            Tuple[bool, int, int]: (allowed, remaining, reset_time)
        """
        now = int(time.time())
        window_start = now - window

        # Get requests for this key
        requests = self._requests.get(key, [])

        # Clean old requests
        requests = [t for t in requests if t > window_start]

        # Check if limit is exceeded
        if len(requests) >= limit:
            reset_time = min(requests) + window if requests else now + window
            return False, 0, reset_time

        # Add current request
        requests.append(now)
        self._requests[key] = requests

        remaining = limit - len(requests)
        reset_time = now + window

        return True, remaining, reset_time

    def reset(self, key: str):
        """Reset rate limit for a specific IP."""
        if key in self._requests:
            del self._requests[key]
