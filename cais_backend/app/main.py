"""
app/main.py

Main FastAPI application for CAIS Code Compliance Backend.
Initializes the API, includes routers, and configures middleware.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api.auth import router as auth_router
from app.api.endpoints import router as endpoints_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="CAIS Code Compliance API",
    description="Backend API for code compliance ingestion, semantic search, and auditing.",
    version="10.0"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],          # Allow all methods
    allow_headers=["*"],          # Allow all headers
)

# Include routers
app.include_router(auth_router)           # Prefix is already /api/v1/auth
app.include_router(endpoints_router)      # Prefix is already /api/v1


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to CAIS Code Compliance API",
        "version": "10.0",
        "docs": "/docs"
    }


# Health check endpoint (also available via endpoints_router, but keep as separate root-level)
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Optional: lifecycle events for startup/shutdown
@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    logger.info("CAIS Code Compliance API starting up...")
    # Database initialization is handled at module import in orchestrator


@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on application shutdown."""
    logger.info("CAIS Code Compliance API shutting down...")
