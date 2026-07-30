"""
Procore Adapter - Procore Marketplace Integration

This module provides the adapter for Procore platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class ProcoreAdapter(BaseAdapter):
    """
    Procore marketplace adapter.

    Procore presents a clean corporate interface, white and soft gray backgrounds,
    with a blue visual line organizing navigation. Dense tables, metrics,
    project cards, and separated modules.
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        company_id: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Procore", config)
        self.client_id = client_id or config.get("client_id")
        self.client_secret = client_secret or config.get("client_secret")
        self.company_id = company_id or config.get("company_id")
        self.base_url = "https://api.procore.com"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Procore API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Procore API using OAuth2.
        """
        try:
            if not self.client_id or not self.client_secret:
                logger.error("Cannot authenticate Procore: Missing credentials")
                return False

            url = f"{self.base_url}/oauth/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            response = await self.client.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.authenticated = True
                logger.info("Authenticated with Procore")
                return True
            else:
                logger.error(f"Procore authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with Procore: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to Procore.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/rest/v1.0/companies/{self.company_id}/documents"

            files = {'file': open(document_path, 'rb')}
            data = {
                'document_type': metadata.get('document_type', 'general'),
                'project_id': metadata.get('project_id'),
                'description': metadata.get('description', '')
            }

            response = await self.client.post(url, files=files, data=data)

            if response.status_code == 201:
                result = response.json()
                logger.info(f"Document uploaded to Procore: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"Procore upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to Procore: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from Procore.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/rest/v1.0/companies/{self.company_id}/documents/{document_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in Procore: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from Procore: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Procore webhook events.
        """
        event_type = payload.get('event', '')
        data = payload.get('data', {})

        logger.info(f"Procore webhook received: {event_type}")

        if event_type == 'document.uploaded':
            return {
                "status": "processed",
                "event": event_type,
                "document_id": data.get('id'),
                "project_id": data.get('project_id')
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
                "message": f"Unhandled event: {event_type}"
            }

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
