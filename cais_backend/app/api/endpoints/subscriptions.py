"""
Subscriptions API Endpoints

This module provides subscription management endpoints for checking plans,
current subscription status, and cancellation.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PaymentRequiredException
from app.models.user import User
from app.schemas.subscription import PlanResponse, SubscriptionResponse, SubscriptionUpdate
from app.api.deps import get_current_active_user
from app.payment.subscription_manager import SubscriptionManager

router = APIRouter()


@router.get("/plans", response_model=list[PlanResponse])
async def get_available_plans():
    """
    Get all available subscription plans.
    """
    return SubscriptionManager.PLANS


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current user's subscription status.
    """
    subscription_manager = SubscriptionManager(db)
    access_info = subscription_manager.get_user_access(current_user)

    return {
        "user_id": str(current_user.id),
        "plan": current_user.subscription_plan,
        "status": "active" if access_info.get('access_granted', False) else "expired",
        "trial_end_date": current_user.trial_end_date,
        "features": access_info.get('features', []),
        "days_left": access_info.get('days_left', 0),
        "is_trial": access_info.get('is_trial', False)
    }


@router.post("/upgrade/{plan}")
async def upgrade_subscription(
    plan: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upgrade to a paid subscription plan.
    """
    if plan not in ["monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose 'monthly' or 'annual'")

    subscription_manager = SubscriptionManager(db)
    result = subscription_manager.activate_subscription(current_user, plan)

    if not result.get('success', False):
        raise HTTPException(status_code=400, detail=result.get('error', 'Subscription activation failed'))

    return {
        "success": True,
        "plan": plan,
        "message": f"Successfully upgraded to {plan} plan"
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel the current subscription.
    """
    if current_user.subscription_plan == "free":
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    subscription_manager = SubscriptionManager(db)
    result = subscription_manager.cancel_subscription(current_user)

    return {
        "success": True,
        "message": "Subscription cancelled successfully"
    }


@router.post("/trial/start")
async def start_trial(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start a 30-day free trial.
    """
    subscription_manager = SubscriptionManager(db)

    if current_user.subscription_plan != "free":
        raise HTTPException(status_code=400, detail="Already has an active subscription")

    if current_user.trial_start_date:
        raise HTTPException(status_code=400, detail="Trial already started")

    subscription_manager.start_trial(current_user)

    return {
        "success": True,
        "message": "30-day free trial started successfully",
        "trial_end_date": current_user.trial_end_date
    }
