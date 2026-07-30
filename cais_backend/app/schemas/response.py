"""
Response Schemas - Generic API Response Models

This module contains generic response schemas used across the API.
"""

from typing import Optional, TypeVar, Generic, List, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Error response schema."""
    status: str = "error"
    message: str
    code: Optional[str] = None
    details: Optional[dict] = None
    timestamp: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str
    timestamp: str
    service: str
    environment: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response schema."""
    status: str = "success"
    message: str
    timestamp: Optional[str] = None
