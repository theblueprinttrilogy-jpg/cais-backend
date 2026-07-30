"""
Subscription Schemas - Pydantic Models for Subscription Endpoints

This module contains Pydantic schemas for subscription management.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class PlanFeature(BaseModel):
    """Plan feature schema."""
    name: str
    description: Optional[str] = None


class PlanResponse(BaseModel):
    """Plan response schema."""
    name: str
    days: int
    price: float
    currency: str
    features: List[str]


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""
    user_id: str
    plan: str
    status: str
    trial_end_date: Optional[datetime] = None
    features: List[str]
    days_left: int
    is_trial: bool


class SubscriptionUpdate(BaseModel):
    """Subscription update schema."""
    plan: Optional[str] = None
    cancel: Optional[bool] = False


class TrialStartResponse(BaseModel):
    """Trial start response schema."""
    success: bool
    message: str
    trial_end_date: Optional[datetime] = None
