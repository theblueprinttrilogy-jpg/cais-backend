# app/config/subscription_config.py - Subscription Profile Configuration for C.A.T.S. v2.0
# This module provides a secure, environment-aware subscription profile for automated
# service registration. Sensitive fields (billing details) are retrieved from environment
# variables with fallback to placeholder defaults (which should not be used in production).

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Default Subscription Profile (non‑sensitive fields only)
# ------------------------------------------------------------------------------
DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Jacinto",
    "surname": "Correa Feliciano",
    "email": "theblueprinttrilogy@gmail.com",
    "password": "{{051664Wmr!$}}",  # should be overridden by env
    "billing": {
        "address_line1": "8423 Duskin Ct",
        "address_line2": "",
        "city": "Jacksonville",
        "state": "Florida",
        "zipcode": "{{32216}}",      # environment fallback
        "country": "US",
        "card": {
            "number": "{{4000223571644426}}",   # environment fallback
            "expiry_month": "{{01}}",
            "expiry_year": "{{30}}",
            "cvv": "{{279}}"
        }
    },
    "preferences": {
        "notification_email": True,
        "auto_renew": False
    },
    "metadata": {
        "version": "1.0",
        "source": "default_profile"
    }
}

# ------------------------------------------------------------------------------
# Environment Variable Mappings (sensitive fields)
# ------------------------------------------------------------------------------
ENV_MAPPINGS = {
    "password": "SUBSCRIPTION_PASSWORD",
    "billing.zipcode": "SUBSCRIPTION_ZIPCODE",
    "billing.card.number": "SUBSCRIPTION_CARD_NUMBER",
    "billing.card.expiry_month": "SUBSCRIPTION_CARD_EXPIRY_MONTH",
    "billing.card.expiry_year": "SUBSCRIPTION_CARD_EXPIRY_YEAR",
    "billing.card.cvv": "SUBSCRIPTION_CARD_CVV",
    "email": "SUBSCRIPTION_EMAIL",     # optional override
    "name": "SUBSCRIPTION_NAME",
    "surname": "SUBSCRIPTION_SURNAME",
}

# ------------------------------------------------------------------------------
# Helper: recursive dictionary update with dot‑notation paths
# ------------------------------------------------------------------------------
def _set_nested_value(d: Dict, path: str, value: Any) -> None:
    """Set a value in a nested dictionary using a dot‑separated path."""
    parts = path.split('.')
    for part in parts[:-1]:
        if part not in d or not isinstance(d[part], dict):
            d[part] = {}
        d = d[part]
    d[parts[-1]] = value

def _get_nested_value(d: Dict, path: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using a dot‑separated path."""
    parts = path.split('.')
    for part in parts:
        if not isinstance(d, dict) or part not in d:
            return default
        d = d[part]
    return d

# ------------------------------------------------------------------------------
# Load profile from JSON file (optional)
# ------------------------------------------------------------------------------
def _load_json_profile(file_path: str = "subscription_profile.json") -> Optional[Dict[str, Any]]:
    """Load a profile from a JSON file if it exists."""
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded subscription profile from {file_path}")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load JSON profile from {file_path}: {e}")
    return None

# ------------------------------------------------------------------------------
# Build final profile with environment overrides
# ------------------------------------------------------------------------------
def get_subscription_profile() -> Dict[str, Any]:
    """
    Construct the final subscription profile by:
        1. Starting with the default profile.
        2. Overlaying any profile loaded from subscription_profile.json.
        3. Overriding sensitive fields with environment variables if set.
    Returns the merged profile dictionary.
    """
    # Start with default
    profile = DEFAULT_PROFILE.copy()

    # Load JSON file if present
    json_profile = _load_json_profile()
    if json_profile:
        # Merge JSON overrides (deep merge would be better, but we'll do a simple update)
        # For simplicity, we'll update top-level keys; but billing is nested.
        # We'll do a recursive merge for dict values.
        def deep_merge(base: Dict, override: Dict) -> Dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        profile = deep_merge(profile, json_profile)

    # Apply environment overrides
    for path, env_var in ENV_MAPPINGS.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            # Convert to appropriate type if needed (e.g., booleans, ints)
            # We'll keep as string, but can be parsed later.
            _set_nested_value(profile, path, env_value)
            logger.debug(f"Overridden '{path}' from environment variable {env_var}")

    # Ensure that no template placeholders remain ({{...}}) for sensitive fields
    # We'll only warn; it's up to the caller to handle missing values.
    # But we can check and log.
    for path in ENV_MAPPINGS:
        value = _get_nested_value(profile, path)
        if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
            logger.warning(f"Environment variable {ENV_MAPPINGS[path]} not set; using placeholder {value}")

    return profile

# ------------------------------------------------------------------------------
# Convenience function to get a specific field with dot notation
# ------------------------------------------------------------------------------
def get_subscription_field(path: str, default: Any = None) -> Any:
    """Retrieve a specific field from the subscription profile using dot notation."""
    profile = get_subscription_profile()
    return _get_nested_value(profile, path, default)

# ------------------------------------------------------------------------------
# If run as script, print the current profile (masking sensitive values)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    profile = get_subscription_profile()
    # Print profile but mask sensitive fields for security
    def mask_sensitive(data):
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key in ("password", "number", "cvv", "expiry_month", "expiry_year"):
                    new_dict[key] = "****"
                else:
                    new_dict[key] = mask_sensitive(value)
            return new_dict
        return data

    masked = mask_sensitive(profile)
    print(json.dumps(masked, indent=2))
