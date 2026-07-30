"""
Security Middleware - Security Headers and Protection

This middleware adds security headers and provides protection against common attacks.
"""

import re
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers and protect against common attacks.

    Features:
    - Security headers (HSTS, XSS protection, etc.)
    - SQL injection pattern detection
    - Path traversal prevention
    - Request sanitization
    """

    # SQL injection patterns
    SQL_PATTERNS = [
        r"SELECT\s+.*\s+FROM",
        r"INSERT\s+INTO",
        r"UPDATE\s+.*\s+SET",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
        r"ALTER\s+TABLE",
        r"UNION\s+SELECT",
        r"OR\s+1\s*=\s*1",
        r"OR\s+'1'\s*=\s*'1'",
        r"--",
        r";\s*DROP",
        r"EXEC\s+",
        r"EXECUTE\s+",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
    ]

    async def dispatch(self, request: Request, call_next):
        """
        Process the request with security checks.

        Args:
            request: Incoming request
            call_next: Next middleware or endpoint

        Returns:
            Response: Outgoing response with security headers
        """
        # Check for SQL injection
        query_string = str(request.query_params)
        if self._has_sql_pattern(query_string):
            return Response(
                content="SQL injection detected",
                status_code=403
            )

        # Check for path traversal
        path = request.url.path
        if self._has_path_traversal(path):
            return Response(
                content="Path traversal detected",
                status_code=403
            )

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response

    def _has_sql_pattern(self, text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        if not text:
            return False
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_path_traversal(self, path: str) -> bool:
        """Check if path contains traversal patterns."""
        for pattern in self.PATH_TRAVERSAL:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
