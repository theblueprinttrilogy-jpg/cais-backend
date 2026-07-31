"""
Autodesk Adapter - Autodesk Forma Integration

This module provides the adapter for Autodesk Forma platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class AutodeskAdapter(BaseAdapter):
    """
    Autodesk Forma marketplace adapter.

    Autodesk Forma has a modern, polished, very visual interface with predominant white
    and side panels framing maps, volumes, and analysis.
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Autodesk Forma", config)
        self.client_id = client_id or config.get("client_id")
        self.client_secret = client_secret or config.get("client_secret")
        self.base_url = "https://developer.api.autodesk.com"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Autodesk API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Autodesk API using OAuth2.
        """
        try:
            if not self.client_id or not self.client_secret:
                logger.error("Cannot authenticate Autodesk: Missing credentials")
                return False

            url = f"{self.base_url}/authentication/v2/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "data:read data:write"
            }

            response = await self.client.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.authenticated = True
                logger.info("Authenticated with Autodesk Forma")
                return True
            else:
                logger.error(f"Autodesk authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with Autodesk: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to Autodesk Forma.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/data/v1/projects/{metadata.get('project_id', 'default')}/items"

            files = {'file': open(document_path, 'rb')}
            data = {
                'name': metadata.get('filename', 'document'),
                'description': metadata.get('description', '')
            }

            response = await self.client.post(url, files=files, data=data)

            if response.status_code == 201:
                result = response.json()
                logger.info(f"Document uploaded to Autodesk: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"Autodesk upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to Autodesk: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from Autodesk Forma.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/data/v1/items/{document_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in Autodesk: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from Autodesk: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Autodesk webhook events.
        """
        event_type = payload.get('event', '')
        data = payload.get('data', {})

        logger.info(f"Autodesk webhook received: {event_type}")

        if event_type == 'document.uploaded':
            return {
                "status": "processed",
                "event": event_type,
                "document_id": data.get('id')
            }
        else:
            return {
                "status": "ignored",
                "event": event_type,
                "message": f"Unhandled event: {event_type}"
            }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
