"""
Payments API Endpoints

This module provides payment processing endpoints for Stripe integration.
Handles payment creation, webhook events, and status checking.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundException, PaymentRequiredException
from app.db.models import User, Payment
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWebhook
from app.api.deps import get_current_active_user
from app.payment.subscription_manager import SubscriptionManager
from app.agents.worm_ledger import WormLedger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a payment intent for subscription.

    Args:
        payment_data: Payment creation data (plan, payment_method)
        current_user: Authenticated user
        db: Database session

    Returns:
        PaymentResponse with client_secret and payment details
    """
    # Validate plan
    if payment_data.plan not in ["monthly", "annual"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan. Choose 'monthly' or 'annual'"
        )

    # Get plan price from SubscriptionManager
    subscription_manager = SubscriptionManager(db)
    plans = subscription_manager.get_all_plans()
    plan_data = None
    for p in plans:
        if p['plan_name'] == payment_data.plan:
            plan_data = p
            break

    if not plan_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan not found"
        )

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

    # In production, this would call Stripe API:
    # import stripe
    # intent = stripe.PaymentIntent.create(
    #     amount=int(plan_data['price'] * 100),
    #     currency=plan_data['currency'],
    #     metadata={'payment_id': str(payment.id), 'user_id': str(current_user.id)}
    # )
    # client_secret = intent.client_secret

    # For now, simulate client secret
    client_secret = f"pi_simulated_{payment.id}_secret"

    # Log to WORM Ledger
    worm_ledger = WormLedger(db)
    worm_ledger.record_action(
        action='PAYMENT_CREATED',
        data={
            'payment_id': str(payment.id),
            'user_id': str(current_user.id),
            'plan': payment_data.plan,
            'amount': plan_data['price']
        },
        user_id=str(current_user.id)
    )

    logger.info(f"Payment created for user {current_user.email}: {payment.id}")

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
) -> Dict[str, Any]:
    """
    Stripe webhook endpoint for payment events.

    Handles payment_intent.succeeded and payment_intent.payment_failed events.
    """
    # In production, verify webhook signature:
    # signature = request.headers.get("Stripe-Signature")
    # webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    # try:
    #     event = stripe.Webhook.construct_event(body, signature, webhook_secret)
    # except ValueError:
    #     raise HTTPException(status_code=400, detail="Invalid payload")
    # except stripe.error.SignatureVerificationError:
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    body = await request.json()
    event_type = body.get('type')
    event_data = body.get('data', {}).get('object', {})

    logger.info(f"Payment webhook received: {event_type}")

    subscription_manager = SubscriptionManager(db)
    worm_ledger = WormLedger(db)

    if event_type == 'payment_intent.succeeded':
        payment_id = event_data.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if payment:
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()
                db.commit()

                # Activate subscription
                user = db.query(User).filter(User.id == payment.user_id).first()
                if user:
                    subscription_manager.activate_subscription(user, payment.plan)

                    # Log to WORM
                    worm_ledger.record_action(
                        action='PAYMENT_SUCCEEDED',
                        data={
                            'payment_id': str(payment.id),
                            'user_id': str(user.id),
                            'plan': payment.plan,
                            'stripe_payment_intent_id': event_data.get('id')
                        },
                        user_id=str(user.id)
                    )

                logger.info(f"Payment {payment_id} succeeded for user {user.email if user else 'unknown'}")

    elif event_type == 'payment_intent.payment_failed':
        payment_id = event_data.get('metadata', {}).get('payment_id')
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if payment:
                payment.status = 'failed'
                payment.error = event_data.get('last_payment_error', {}).get('message', 'Payment failed')
                db.commit()

                # Log to WORM
                worm_ledger.record_action(
                    action='PAYMENT_FAILED',
                    data={
                        'payment_id': str(payment.id),
                        'user_id': str(payment.user_id),
                        'error': payment.error
                    },
                    user_id=str(payment.user_id)
                )

                logger.warning(f"Payment {payment_id} failed: {payment.error}")

    return {"status": "received"}


@router.get("/status/{payment_id}", response_model=PaymentResponse)
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the status of a payment.

    Args:
        payment_id: Payment UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        PaymentResponse with payment details
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise NotFoundException("Payment", payment_id)

    # Check authorization: user can view their own payments, superuser can view all
    if payment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )

    return {
        "id": str(payment.id),
        "client_secret": None,  # Not exposed after creation
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "plan": payment.plan
    }
