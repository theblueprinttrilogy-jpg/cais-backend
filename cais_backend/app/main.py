"""
FastAPI application entry point for the CAIS Backend.

Initialises the API, configures CORS, registers routers,
and manages graceful shutdown of asynchronous resources.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import dashboard
from app.core.config import settings
from app.services.evidence_processor import evidence_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup: nothing special needed yet
    logger.info("CAIS Backend starting up...")
    yield
    # Shutdown: gracefully close RabbitMQ connection
    logger.info("CAIS Backend shutting down...")
    await evidence_processor.close()
    logger.info("Shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="CAIS Backend API",
    description="Code Compliance Automated Inspection System - Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
# Allow local development origins and optionally a list from environment
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
# If a CORS_ORIGINS environment variable is set, parse and override
if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
    allowed_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dashboard.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "cais-backend"}
