"""
Subscription Manager - Payment and Subscription Management

Handles 30-day free trial, monthly and annual subscriptions.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from app.db.models import User
from app.agents.worm_ledger import WormLedger

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Subscription Manager for CAIS Code Compliance.

    Plans:
    1. Free Trial: 30 days
    2. Monthly: $299/month
    3. Annual: $2,999/year
    """

    PLANS = {
        'free': {
            'name': 'Free Trial',
            'days': 30,
            'price': 0.0,
            'currency': 'USD',
            'features': ['Basic Analysis', '1 Project', 'Forensic Facts Dossier']
        },
        'monthly': {
            'name': 'Monthly Plan',
            'days': 30,
            'price': 299.00,
            'currency': 'USD',
            'features': ['Unlimited Projects', 'All Agents', 'Full Reports', 'Priority Support']
        },
        'annual': {
            'name': 'Annual Plan',
            'days': 365,
            'price': 2999.00,
            'currency': 'USD',
            'features': [
                'Unlimited Projects', 'All Agents', 'Full Reports',
                'Priority Support', '2 Months Free', 'Dedicated Account Manager'
            ]
        }
    }

    def __init__(self, db_session: Session):
        """
        Initialize the subscription manager.

        Args:
            db_session: SQLAlchemy session for database operations
        """
        self.db = db_session
        self.worm_ledger = WormLedger(db_session)

    def start_trial(self, user: User) -> Dict[str, Any]:
        """
        Start a 30-day free trial for a new user.

        Args:
            user: User object

        Returns:
            dict: Status and trial end date
        """
        trial_end = datetime.utcnow() + timedelta(days=30)

        user.trial_start_date = datetime.utcnow()
        user.trial_end_date = trial_end
        user.subscription_plan = 'free'
        self.db.commit()

        # Log to WORM Ledger
        self.worm_ledger.record_action(
            action='TRIAL_STARTED',
            data={
                'user_id': str(user.id),
                'email': user.email,
                'trial_end_date': trial_end.isoformat()
            },
            user_id=str(user.id)
        )

        logger.info(f"Started 30-day trial for user: {user.email}")
        return {
            'status': 'trial_started',
            'trial_end_date': trial_end.isoformat()
        }

    def is_trial_active(self, user: User) -> bool:
        """Check if the user's trial is still active."""
        if user.subscription_plan != 'free':
            return False
        if not user.trial_end_date:
            return False
        return datetime.utcnow() < user.trial_end_date

    def get_trial_days_left(self, user: User) -> int:
        """Get the number of days left in the trial."""
        if not user.trial_end_date:
            return 0
        days_left = (user.trial_end_date - datetime.utcnow()).days
        return max(0, days_left)

    def activate_subscription(self, user: User, plan: str) -> Dict[str, Any]:
        """
        Activate a paid subscription.

        Args:
            user: User object
            plan: 'monthly' or 'annual'

        Returns:
            dict: Success status and plan details
        """
        if plan not in self.PLANS:
            return {'success': False, 'error': f'Invalid plan: {plan}'}

        if plan == 'free':
            return {'success': False, 'error': 'Cannot activate free as paid subscription'}

        plan_data = self.PLANS[plan]

        # Update user
        user.subscription_plan = plan
        user.trial_end_date = None  # Trial ends when subscription starts
        self.db.commit()

        # Log to WORM Ledger
        self.worm_ledger.record_action(
            action='SUBSCRIPTION_ACTIVATED',
            data={
                'user_id': str(user.id),
                'email': user.email,
                'plan': plan,
                'price': plan_data['price']
            },
            user_id=str(user.id)
        )

        logger.info(f"Activated {plan} subscription for user: {user.email}")
        return {
            'success': True,
            'plan': plan,
            'price': plan_data['price']
        }

    def cancel_subscription(self, user: User) -> Dict[str, Any]:
        """
        Cancel a user's subscription.

        Args:
            user: User object

        Returns:
            dict: Success status and old plan
        """
        old_plan = user.subscription_plan

        if old_plan == 'free':
            return {'success': False, 'error': 'No active subscription to cancel'}

        user.subscription_plan = 'free'
        self.db.commit()

        # Log to WORM Ledger
        self.worm_ledger.record_action(
            action='SUBSCRIPTION_CANCELLED',
            data={
                'user_id': str(user.id),
                'email': user.email,
                'old_plan': old_plan
            },
            user_id=str(user.id)
        )

        logger.info(f"Cancelled subscription for user: {user.email}")
        return {'success': True, 'old_plan': old_plan}

    def get_user_access(self, user: User) -> Dict[str, Any]:
        """
        Get access information for a user.

        Returns:
            dict: Access details including plan, days left, features
        """
        has_active_trial = self.is_trial_active(user)
        has_subscription = user.subscription_plan in ['monthly', 'annual']

        if has_active_trial:
            days_left = self.get_trial_days_left(user)
            return {
                'access_granted': True,
                'plan': 'free_trial',
                'days_left': days_left,
                'is_trial': True,
                'features': self.PLANS['free']['features']
            }
        elif has_subscription:
            plan = user.subscription_plan
            return {
                'access_granted': True,
                'plan': plan,
                'days_left': 'Unlimited',
                'is_trial': False,
                'features': self.PLANS.get(plan, {}).get('features', [])
            }
        else:
            return {
                'access_granted': False,
                'plan': 'expired',
                'days_left': 0,
                'is_trial': False,
                'features': []
            }

    def check_access(self, user: User) -> bool:
        """Check if a user has active access."""
        access_info = self.get_user_access(user)
        return access_info.get('access_granted', False)

    def get_all_plans(self) -> list:
        """Get all available plans."""
        return [
            {'plan_name': plan, **data}
            for plan, data in self.PLANS.items()
        ]
