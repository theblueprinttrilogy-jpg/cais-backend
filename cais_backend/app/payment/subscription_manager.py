"""
Subscription Manager - Payment and Subscription Management

Handles 30-day free trial, monthly and annual subscriptions.

Based on CAIS CODE COMPLIANCE WORKFLOW - Section 3.2
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.db.models import Base
from app.services.worm_ledger import WORMService

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
            'price': 0,
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
            'features': ['Unlimited Projects', 'All Agents', 'Full Reports', 'Priority Support', '2 Months Free', 'Dedicated Account Manager']
        }
    }

    def __init__(self, db_session=None, worm_service: Optional[WORMService] = None):
        self.db_session = db_session
        self.worm_service = worm_service

    def start_trial(self, user) -> dict:
        """Start a 30-day free trial for a new user."""
        trial_end = datetime.now() + timedelta(days=30)

        # Update user in database
        if hasattr(user, 'trial_start_date'):
            user.trial_start_date = datetime.now()
            user.trial_end_date = trial_end
            user.subscription_plan = 'free'
            if self.db_session:
                self.db_session.commit()

        self._log_to_worm('TRIAL_STARTED', {
            'user_id': str(getattr(user, 'id', 'unknown')),
            'email': getattr(user, 'email', 'unknown'),
            'trial_end_date': trial_end.isoformat()
        })

        logger.info(f"Started 30-day trial for user: {getattr(user, 'email', 'unknown')}")
        return {'status': 'trial_started', 'trial_end_date': trial_end.isoformat()}

    def is_trial_active(self, user) -> bool:
        """Check if the user's trial is still active."""
        if not hasattr(user, 'trial_end_date') or not user.trial_end_date:
            return False
        if getattr(user, 'subscription_plan', 'free') != 'free':
            return False
        return datetime.now() < user.trial_end_date

    def get_trial_days_left(self, user) -> int:
        """Get the number of days left in the trial."""
        if not hasattr(user, 'trial_end_date') or not user.trial_end_date:
            return 0
        days_left = (user.trial_end_date - datetime.now()).days
        return max(0, days_left)

    def activate_subscription(self, user, plan: str) -> dict:
        """Activate a paid subscription."""
        if plan not in self.PLANS:
            return {'success': False, 'error': f'Invalid plan: {plan}'}

        if plan == 'free':
            return {'success': False, 'error': 'Cannot activate free as paid subscription'}

        plan_data = self.PLANS[plan]

        if hasattr(user, 'subscription_plan'):
            user.subscription_plan = plan
            user.trial_end_date = None
            if self.db_session:
                self.db_session.commit()

        self._log_to_worm('SUBSCRIPTION_ACTIVATED', {
            'user_id': str(getattr(user, 'id', 'unknown')),
            'email': getattr(user, 'email', 'unknown'),
            'plan': plan,
            'price': plan_data['price']
        })

        logger.info(f"Activated {plan} subscription for user: {getattr(user, 'email', 'unknown')}")
        return {'success': True, 'plan': plan, 'price': plan_data['price']}

    def cancel_subscription(self, user) -> dict:
        """Cancel a user's subscription."""
        old_plan = getattr(user, 'subscription_plan', 'unknown')

        if hasattr(user, 'subscription_plan'):
            user.subscription_plan = 'free'
            if self.db_session:
                self.db_session.commit()

        self._log_to_worm('SUBSCRIPTION_CANCELLED', {
            'user_id': str(getattr(user, 'id', 'unknown')),
            'email': getattr(user, 'email', 'unknown'),
            'old_plan': old_plan
        })

        logger.info(f"Cancelled subscription for user: {getattr(user, 'email', 'unknown')}")
        return {'success': True, 'old_plan': old_plan}

    def get_user_access(self, user) -> Dict[str, Any]:
        """Get access information for a user."""
        has_active_trial = self.is_trial_active(user)
        has_subscription = getattr(user, 'subscription_plan', 'free') in ['monthly', 'annual']

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
            plan = getattr(user, 'subscription_plan', 'monthly')
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

    def check_access(self, user) -> bool:
        """Check if a user has active access."""
        access_info = self.get_user_access(user)
        return access_info.get('access_granted', False)

    def get_all_plans(self) -> list:
        """Get all available plans."""
        return [
            {'plan_name': plan, **data}
            for plan, data in self.PLANS.items()
        ]

    def _log_to_worm(self, action: str, data: dict):
        """Log to WORM Ledger."""
        if self.worm_service:
            try:
                import asyncio
                asyncio.create_task(
                    self.worm_service.add_entry(
                        evidence_gcs_uri=f"subscription_event_{datetime.now().timestamp()}",
                        violation_codes={
                            'action': action,
                            'data': data,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Failed to log to WORM Ledger: {e}")
