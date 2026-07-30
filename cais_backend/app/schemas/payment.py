"""
Payment Schemas - Pydantic Models for Payment Endpoints

This module contains Pydantic schemas for payment processing.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Payment creation schema."""
    plan: str = Field(..., description="monthly or annual")
    payment_method: Optional[str] = "stripe"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentResponse(BaseModel):
    """Payment response schema."""
    id: str
    client_secret: str
    amount: float
    currency: str
    status: str
    plan: str
    payment_method: Optional[str] = None
    created_at: Optional[datetime] = None


class PaymentWebhook(BaseModel):
    """Payment webhook schema."""
    event_type: str
    payment_id: str
    status: str
    metadata: Optional[dict] = None
    timestamp: Optional[datetime] = None


class PaymentStatusResponse(BaseModel):
    """Payment status response schema."""
    payment_id: str
    status: str
    plan: str
    amount: float
    currency: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
