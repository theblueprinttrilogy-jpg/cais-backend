"""
Encryption Core - Data Encryption Utilities

This module provides encryption utilities for sensitive data.
"""

import base64
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


class EncryptionManager:
    """
    Manager for encryption operations.
    """

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self._fernet = None
        self._init_fernet()

    def _init_fernet(self):
        """Initialize Fernet encryption."""
        # Derive a key from the secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"cais_salt_2026",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: String to encrypt

        Returns:
            str: Encrypted string (base64)
        """
        if not data:
            return data

        encrypted = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted_data: Encrypted string

        Returns:
            str: Decrypted string
        """
        if not encrypted_data:
            return encrypted_data

        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            return ""

    def hash_data(self, data: str) -> str:
        """
        Hash data using SHA-256.

        Args:
            data: String to hash

        Returns:
            str: SHA-256 hash
        """
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate a secure token.

        Args:
            length: Length of the token

        Returns:
            str: Secure token
        """
        return secrets.token_urlsafe(length)


# Singleton instance
encryption_manager = EncryptionManager()
