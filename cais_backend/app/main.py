"""
FastAPI application entry point for the CAIS Code Compliance backend.

Initialises the API, configures CORS, registers routers,
and manages lifecycle events for database and WORM ledger.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import dashboard
from app.core.config import settings
from app.db.session import engine
from app.services.evidence_processor import evidence_processor
from app.services.worm_ledger import WORMService
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    logger.info("CAIS Backend starting up...")

    # Initialize WORM service (optional: pre-warm connections)
    worm_service = WORMService(AsyncSessionLocal)
    logger.info("WORM service ready")

    yield

    # Shutdown: gracefully close RabbitMQ connection and database engine
    logger.info("CAIS Backend shutting down...")
    await evidence_processor.close()
    await engine.dispose()
    logger.info("Shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="CAIS Backend API",
    description="Code Compliance Automated Inspection System - Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
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
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])


# Health check endpoint
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "cais-backend"}


# Root endpoint – simple redirect
@app.get("/")
async def root():
    return {"message": "CAIS Backend API is running", "docs": "/docs"}
