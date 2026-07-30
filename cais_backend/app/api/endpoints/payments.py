"""
Payments API Endpoints

This module provides payment processing endpoints for Stripe integration.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PaymentRequiredException
from app.models.user import User
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWebhook
from app.api.deps import get_current_active_user
from app.payment.subscription_manager import SubscriptionManager

router = APIRouter()


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a payment intent for subscription.
    """
    # Validate plan
    if payment_data.plan not in ["monthly", "annual"]:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Get plan price
    plan_data = SubscriptionManager.PLANS.get(payment_data.plan)
    if not plan_data:
        raise HTTPException(status_code=400, detail="Plan not found")

    # In production, this would integrate with Stripe
    # For now, we simulate a payment

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=plan_data['price'],
        currency=plan_data['currency'],
        status='pending',
        plan=payment_data.plan,
        payment_method=payment_data.payment_method or 'stripe'
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Simulate Stripe client secret
    client_secret = f"pi_simulated_{payment.id}_secret"

    return {
        "id": str(payment.id),
        "client_secret": client_secret,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "plan": payment.plan
    }


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stripe webhook endpoint for payment events.
    """
    # In production, verify webhook signature
    body = await request.json()

    event_type = body.get('type')
    event_data = body.get('data', {}).get('object', {})

    if event_type == 'payment_intent.succeeded':
        payment_id = event_data.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if payment:
                payment.status = 'completed'
                db.commit()

                # Activate subscription
                user = db.query(User).filter(User.id == payment.user_id).first()
                if user:
                    subscription_manager = SubscriptionManager(db)
                    subscription_manager.activate_subscription(
                        user,
                        payment.plan,
                        stripe_subscription_id=event_data.get('id')
                    )

    elif event_type == 'payment_intent.payment_failed':
        payment_id = event_data.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if payment:
                payment.status = 'failed'
                db.commit()

    return {"status": "received"}


@router.get("/status/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of a payment.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    return payment
