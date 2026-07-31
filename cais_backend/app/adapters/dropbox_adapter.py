"""
Dropbox Adapter - Dropbox Platform Integration

This module provides the adapter for Dropbox platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class DropboxAdapter(BaseAdapter):
    """
    Dropbox marketplace adapter.

    Dropbox has a minimalist and very clean interface, centered on a list of
    folders and files, with a simple sidebar and plenty of white space.
    """

    def __init__(
        self,
        app_key: str = None,
        app_secret: str = None,
        refresh_token: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Dropbox", config)
        self.app_key = app_key or config.get("app_key")
        self.app_secret = app_secret or config.get("app_secret")
        self.refresh_token = refresh_token or config.get("refresh_token")
        self.base_url = "https://api.dropboxapi.com/2"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Dropbox API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Dropbox API using OAuth2.
        """
        try:
            if not self.app_key or not self.app_secret or not self.refresh_token:
                logger.error("Cannot authenticate Dropbox: Missing credentials")
                return False

            url = "https://api.dropboxapi.com/oauth2/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.app_key,
                "client_secret": self.app_secret
            }

            response = await self.client.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.authenticated = True
                logger.info("Authenticated with Dropbox")
                return True
            else:
                logger.error(f"Dropbox authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with Dropbox: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to Dropbox.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/files/upload"
            dropbox_path = metadata.get('dropbox_path', '/')
            filename = metadata.get('filename', 'document')

            with open(document_path, 'rb') as f:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/octet-stream",
                    "Dropbox-API-Arg": json.dumps({
                        "path": f"{dropbox_path}/{filename}",
                        "mode": "add",
                        "autorename": True
                    })
                }
                response = await self.client.post(url, headers=headers, content=f.read())

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Document uploaded to Dropbox: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"Dropbox upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to Dropbox: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from Dropbox.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/files/get_metadata"
            data = {"path": f"/{document_id}"}
            response = await self.client.post(url, json=data)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in Dropbox: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from Dropbox: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Dropbox webhook events.
        """
        delta = payload.get('delta', {})
        entries = delta.get('entries', [])

        logger.info(f"Dropbox webhook received with {len(entries)} entries")

        for entry in entries:
            logger.info(f"Dropbox file event: {entry.get('path', 'unknown')}")

        return {"status": "received"}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
