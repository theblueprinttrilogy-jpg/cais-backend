"""
Security Core - Security Utilities

This module provides security utilities including:
- CSRF protection
- CORS configuration
- Security headers
- Input sanitization
"""

import re
import secrets
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    """
    return secrets.token_urlsafe(32)


def sanitize_input(text: str) -> str:
    """
    Sanitize input to prevent XSS attacks.
    """
    if not text:
        return text

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Escape special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')

    return text


def validate_password_strength(password: str) -> dict:
    """
    Validate password strength.

    Returns:
        dict: {
            "valid": bool,
            "message": str,
            "score": int (0-4)
        }
    """
    score = 0
    messages = []

    if len(password) < 8:
        messages.append("Password must be at least 8 characters")
    else:
        score += 1

    if re.search(r'[A-Z]', password):
        score += 1
    else:
        messages.append("Password must contain at least one uppercase letter")

    if re.search(r'[a-z]', password):
        score += 1
    else:
        messages.append("Password must contain at least one lowercase letter")

    if re.search(r'[0-9]', password):
        score += 1
    else:
        messages.append("Password must contain at least one number")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        messages.append("Password must contain at least one special character")

    is_valid = score >= 3

    return {
        "valid": is_valid,
        "message": ", ".join(messages) if not is_valid else "Password is strong",
        "score": score
    }


def mask_email(email: str) -> str:
    """
    Mask an email address for display.
    """
    if not email:
        return email

    parts = email.split('@')
    if len(parts) != 2:
        return email

    username, domain = parts
    if len(username) <= 2:
        masked_username = username[0] + '*' * len(username[1:])
    else:
        masked_username = username[0] + '*' * (len(username) - 2) + username[-1]

    return f"{masked_username}@{domain}"
