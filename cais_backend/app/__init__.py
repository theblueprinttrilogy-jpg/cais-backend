"""
CAIS Code Compliance - Application Package Initializer

This module initializes the CAIS application package.
It exposes the FastAPI application instance for use by uvicorn and other tools.
"""

__version__ = "10.0.0"
__author__ = "CAIS Team"

# Import the application instance directly
from .main import app

# Export the app as the main entry point
# For uvicorn, use: uvicorn app:app --reload
# For create_app pattern, we keep compatibility if needed
def create_app():
    """Compatibility function to match expected interface."""
    return app

__all__ = [
    "app",
    "create_app",
]
