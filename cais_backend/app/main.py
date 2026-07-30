"""
CAIS Code Compliance - Main Application Entry Point

CAIS CODE COMPLIANCE is a forensic evidence generation tool for construction code violations.
It receives documents from 21 platforms, analyzes them visually and semantically,
detects code violations using AI, generates forensic evidence, and delivers a
Forensic Facts Dossier without CAIS commentary.

Version: 10.0
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from config import settings
from app.core.exceptions import AppException
from app.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database connection pool
    # Initialize Redis cache connection
    # Initialize RabbitMQ connection
    # Initialize Ollama connection

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Forensic evidence generation for construction code violations",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
        "service": settings.APP_NAME
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "documentation": "/docs",
        "health": "/health"
    }


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": time.time()
        }
    )
