"""
CAIS Code Compliance - Entry Point for Uvicorn

This is the main entry point for running the application with uvicorn.
"""

import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
