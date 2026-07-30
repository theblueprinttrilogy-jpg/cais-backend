"""
CORS Middleware - Cross-Origin Resource Sharing

This middleware handles CORS configuration for the API.
"""

from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from app.core.config import settings


def setup_cors(app):
    """
    Configure CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
        max_age=3600,
    )
