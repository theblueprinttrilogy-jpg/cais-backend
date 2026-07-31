"""
PlanGrid Adapter - PlanGrid Platform Integration

This module provides the adapter for PlanGrid platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class PlanGridAdapter(BaseAdapter):
    """
    PlanGrid marketplace adapter.

    PlanGrid has an interface very oriented to plans, with a typical capture showing
    a tablet or viewer with a technical drawing background and overlaid menus.
    """

    def __init__(
        self,
        api_key: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("PlanGrid", config)
        self.api_key = api_key or config.get("api_key")
        self.base_url = "https://api.plangrid.com/v1"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for PlanGrid API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with PlanGrid API using API key.
        """
        try:
            if not self.api_key:
                logger.error("Cannot authenticate PlanGrid: Missing API key")
                return False

            response = await self.client.get(f"{self.base_url}/auth/verify")
            if response.status_code == 200:
                self.authenticated = True
                logger.info("Authenticated with PlanGrid")
                return True
            else:
                logger.error(f"PlanGrid authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with PlanGrid: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to PlanGrid.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/projects/{metadata.get('project_id', 'default')}/documents"

            files = {'file': open(document_path, 'rb')}
            data = {
                'name': metadata.get('filename', 'document'),
                'sheet_number': metadata.get('sheet_number', '')
            }

            response = await self.client.post(url, files=files, data=data)

            if response.status_code == 201:
                result = response.json()
                logger.info(f"Document uploaded to PlanGrid: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"PlanGrid upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to PlanGrid: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from PlanGrid.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/documents/{document_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in PlanGrid: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from PlanGrid: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle PlanGrid webhook events.
        """
        event_type = payload.get('event', '')
        data = payload.get('data', {})

        logger.info(f"PlanGrid webhook received: {event_type}")

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
