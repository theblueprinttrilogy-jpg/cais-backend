"""
API Package - FastAPI Routes and Endpoints

This package contains all API routes for the CAIS Code Compliance system.
"""

from app.api.v1.router import api_router

__all__ = ["api_router"]
