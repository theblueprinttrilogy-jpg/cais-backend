"""
Logging Middleware - Request/Response Logging

This middleware logs all incoming requests and outgoing responses
for monitoring and debugging purposes.
"""

import logging
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses.

    Logs:
    - Request method and path
    - Response status code
    - Processing time
    - Client IP address
    - User agent
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and log details.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response: Outgoing response
        """
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        user_agent = request.headers.get("User-Agent", "unknown")

        # Log request
        logger.info(
            f"Request: {method} {path} - Client: {client_ip} - UA: {user_agent}"
        )

        # Process request
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Response: {method} {path} - Status: {response.status_code} - "
                f"Time: {process_time:.2f}ms - Client: {client_ip}"
            )

            # Add processing time header
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

            return response

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Error: {method} {path} - Error: {str(e)} - "
                f"Time: {process_time:.2f}ms - Client: {client_ip}"
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Args:
            request: Incoming request

        Returns:
            str: Client IP address
        """
        # Check for X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        if request.client:
            return request.client.host

        return "0.0.0.0"
