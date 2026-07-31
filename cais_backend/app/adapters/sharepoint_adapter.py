"""
SharePoint Adapter - Microsoft SharePoint Integration

This module provides the adapter for SharePoint platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class SharePointAdapter(BaseAdapter):
    """
    SharePoint marketplace adapter.

    SharePoint looks like a Microsoft corporate portal: white dominant, blue accents,
    side or top navigation, and well-separated content blocks.
    """

    def __init__(
        self,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        site_id: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("SharePoint", config)
        self.tenant_id = tenant_id or config.get("tenant_id")
        self.client_id = client_id or config.get("client_id")
        self.client_secret = client_secret or config.get("client_secret")
        self.site_id = site_id or config.get("site_id")
        self.base_url = f"https://graph.microsoft.com/v1.0"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Graph API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API using OAuth2.
        """
        try:
            if not self.tenant_id or not self.client_id or not self.client_secret:
                logger.error("Cannot authenticate SharePoint: Missing credentials")
                return False

            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }

            response = await self.client.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.authenticated = True
                logger.info("Authenticated with SharePoint")
                return True
            else:
                logger.error(f"SharePoint authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with SharePoint: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to SharePoint.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            site_id = self.site_id or metadata.get('site_id')
            drive_id = metadata.get('drive_id', '')
            folder_id = metadata.get('folder_id', '')

            url = f"{self.base_url}/sites/{site_id}/drives/{drive_id}/items/{folder_id}:/{metadata.get('filename', 'document')}:/content"

            with open(document_path, 'rb') as f:
                response = await self.client.put(url, content=f.read())

            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Document uploaded to SharePoint: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"SharePoint upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to SharePoint: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from SharePoint.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            site_id = self.site_id
            url = f"{self.base_url}/sites/{site_id}/drives/items/{document_id}"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in SharePoint: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from SharePoint: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SharePoint webhook events.
        """
        event_type = payload.get('eventType', '')
        data = payload.get('value', {})

        logger.info(f"SharePoint webhook received: {event_type}")

        if event_type in ['file.created', 'file.updated']:
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
