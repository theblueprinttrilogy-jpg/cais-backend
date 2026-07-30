"""
Marketplace Adapter - Generic Marketplace Integration

This module provides a generic adapter for marketplace integrations.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class MarketplaceAdapter(BaseAdapter):
    """
    Generic marketplace adapter for API-based integrations.
    """

    def __init__(
        self,
        name: str,
        api_url: str,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name, config)
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with the marketplace API.
        """
        try:
            if not self.api_key:
                logger.error(f"Cannot authenticate {self.name}: No API key provided")
                return False

            response = await self.client.get(f"{self.api_url}/auth/verify")
            if response.status_code == 200:
                self.authenticated = True
                logger.info(f"Authenticated with {self.name}")
                return True
            else:
                logger.error(f"Authentication failed for {self.name}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with {self.name}: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to the marketplace.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.api_url}/documents"

            files = {'file': open(document_path, 'rb')}
            data = {'metadata': json.dumps(metadata)}

            response = await self.client.post(
                url,
                files=files,
                data=data
            )

            if response.status_code == 201:
                result = response.json()
                logger.info(f"Document uploaded to {self.name}: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"Upload failed for {self.name}: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to {self.name}: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the marketplace.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.api_url}/documents/{document_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in {self.name}: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from {self.name}: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook events from the marketplace.
        """
        event_type = payload.get('event', 'unknown')
        data = payload.get('data', {})

        logger.info(f"Webhook received from {self.name}: {event_type}")

        if event_type == 'document.uploaded':
            return {
                "status": "processed",
                "event": event_type,
                "document_id": data.get('id')
            }
        elif event_type == 'document.updated':
            return {
                "status": "processed",
                "event": event_type,
                "document_id": data.get('id')
            }
        else:
            return {
                "status": "ignored",
                "event": event_type,
                "message": "Unhandled event type"
            }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
