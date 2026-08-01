"""
Subscriptions API Endpoints

This module provides subscription management endpoints for checking plans,
current subscription status, trial activation, and cancellation.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException, PaymentRequiredException
from app.db.models import User
from app.schemas.subscription import PlanResponse, SubscriptionResponse, SubscriptionUpdate
from app.api.deps import get_current_active_user
from app.payment.subscription_manager import SubscriptionManager
from app.agents.worm_ledger import WormLedger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=List[PlanResponse])
async def get_available_plans() -> List[Dict[str, Any]]:
    """
    Get all available subscription plans.

    Returns:
        List of plans with name, price, currency, days, and features.
    """
    # We instantiate without db just to get static plan data
    # We need a db session, but for static data we can just return the constant
    # However, we'll use a temporary manager to keep consistency
    # Actually, SubscriptionManager.PLANS is static
    plans = []
    for plan_name, plan_data in SubscriptionManager.PLANS.items():
        plans.append({
            "plan_name": plan_name,
            "name": plan_data.get("name", plan_name),
            "price": plan_data.get("price", 0.0),
            "currency": plan_data.get("currency", "USD"),
            "days": plan_data.get("days", 0),
            "features": plan_data.get("features", [])
        })
    return plans


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current user's subscription status.

    Returns:
        Subscription details including plan, status, days left, features.
    """
    subscription_manager = SubscriptionManager(db)
    access_info = subscription_manager.get_user_access(current_user)

    # Determine status string
    if access_info.get('access_granted', False):
        if access_info.get('is_trial', False):
            status_str = "trial"
        else:
            status_str = "active"
    else:
        status_str = "expired"

    return {
        "user_id": str(current_user.id),
        "plan": current_user.subscription_plan,
        "status": status_str,
        "trial_end_date": current_user.trial_end_date,
        "features": access_info.get('features', []),
        "days_left": access_info.get('days_left', 0),
        "is_trial": access_info.get('is_trial', False)
    }


@router.post("/trial/start")
async def start_trial(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Start a 30-day free trial for the user.

    Only available for users with 'free' plan and no existing trial.
    """
    subscription_manager = SubscriptionManager(db)

    # Check if user already has an active subscription
    if current_user.subscription_plan != "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription plan"
        )

    # Check if trial already started
    if current_user.trial_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trial already started"
        )

    result = subscription_manager.start_trial(current_user)

    return {
        "success": True,
        "message": "30-day free trial started successfully",
        "trial_end_date": result.get('trial_end_date')
    }


@router.post("/upgrade/{plan}")
async def upgrade_subscription(
    plan: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Upgrade to a paid subscription plan.

    Args:
        plan: 'monthly' or 'annual'

    Returns:
        Success status and plan details.
    """
    if plan not in ["monthly", "annual"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Choose 'monthly' or 'annual'"
        )

    subscription_manager = SubscriptionManager(db)

    # Check if already on this plan
    if current_user.subscription_plan == plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already on {plan} plan"
        )

    result = subscription_manager.activate_subscription(current_user, plan)

    if not result.get('success', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Subscription activation failed')
        )

    return {
        "success": True,
        "plan": plan,
        "message": f"Successfully upgraded to {plan} plan",
        "price": result.get('price')
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Cancel the current subscription.

    Returns:
        Success status and old plan.
    """
    subscription_manager = SubscriptionManager(db)

    if current_user.subscription_plan == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel"
        )

    result = subscription_manager.cancel_subscription(current_user)

    if not result.get('success', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Subscription cancellation failed')
        )

    return {
        "success": True,
        "message": "Subscription cancelled successfully",
        "old_plan": result.get('old_plan')
    }
