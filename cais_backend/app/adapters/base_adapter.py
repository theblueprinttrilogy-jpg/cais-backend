"""
Base Adapter - Abstract Base Class for Marketplace Integrations

This module provides the base class for all marketplace adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Abstract base class for marketplace adapters.

    Each marketplace adapter must implement:
    - authenticate(): Authenticate with the marketplace
    - upload_document(): Upload a document to the marketplace
    - get_document(): Retrieve a document from the marketplace
    - webhook_handler(): Handle webhook events from the marketplace
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter.

        Args:
            name: Name of the marketplace
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.authenticated = False
        self.access_token = None

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the marketplace.

        Returns:
            bool: True if authentication was successful
        """
        pass

    @abstractmethod
    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to the marketplace.

        Args:
            document_path: Path to the document file
            metadata: Document metadata

        Returns:
            dict: Upload result with document ID and URL
        """
        pass

    @abstractmethod
    async def get_document(
        self,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the marketplace.

        Args:
            document_id: Document identifier

        Returns:
            dict: Document data or None if not found
        """
        pass

    @abstractmethod
    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook events from the marketplace.

        Args:
            payload: Webhook payload

        Returns:
            dict: Response to send back to the marketplace
        """
        pass

    def is_authenticated(self) -> bool:
        """Check if the adapter is authenticated."""
        return self.authenticated

    def get_name(self) -> str:
        """Get the adapter name."""
        return self.name

    def get_config(self) -> Dict[str, Any]:
        """Get the adapter configuration."""
        return self.config
