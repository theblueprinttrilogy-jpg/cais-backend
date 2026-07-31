"""
Google Workspace Adapter - Google Workspace Integration

This module provides the adapter for Google Workspace platform integration.
"""

from typing import Dict, Any, Optional
import json
import httpx
import logging

from app.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class GoogleWorkspaceAdapter(BaseAdapter):
    """
    Google Workspace marketplace adapter.

    Google Workspace has a familiar and lightweight look, with email, document,
    and apps interfaces grouped in a clean environment.
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("Google Workspace", config)
        self.client_id = client_id or config.get("client_id")
        self.client_secret = client_secret or config.get("client_secret")
        self.refresh_token = refresh_token or config.get("refresh_token")
        self.base_url = "https://www.googleapis.com/drive/v3"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Google Drive API."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API using OAuth2.
        """
        try:
            if not self.client_id or not self.client_secret or not self.refresh_token:
                logger.error("Cannot authenticate Google Workspace: Missing credentials")
                return False

            url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }

            response = await self.client.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                self.authenticated = True
                logger.info("Authenticated with Google Workspace")
                return True
            else:
                logger.error(f"Google Workspace authentication failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error authenticating with Google Workspace: {e}")
            return False

    async def upload_document(
        self,
        document_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload a document to Google Drive (Workspace).
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"

            with open(document_path, 'rb') as f:
                files = {
                    'metadata': (None, json.dumps({
                        'name': metadata.get('filename', 'document'),
                        'parents': [metadata.get('folder_id', 'root')]
                    }), 'application/json'),
                    'file': (metadata.get('filename', 'document'), f, 'application/octet-stream')
                }
                headers = {
                    "Authorization": f"Bearer {self.access_token}"
                }
                response = await self.client.post(url, headers=headers, files=files)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Document uploaded to Google Workspace: {result.get('id', 'unknown')}")
                return result
            else:
                logger.error(f"Google Workspace upload failed: {response.status_code}")
                return {"error": "Upload failed", "status": response.status_code}

        except Exception as e:
            logger.error(f"Error uploading to Google Workspace: {e}")
            return {"error": str(e)}

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from Google Drive.
        """
        try:
            if not self.authenticated:
                await self.authenticate()

            url = f"{self.base_url}/files/{document_id}?fields=id,name,mimeType,size,webViewLink"
            response = await self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Document not found in Google Workspace: {document_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting document from Google Workspace: {e}")
            return None

    async def webhook_handler(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Google Drive webhook events.
        """
        event_type = payload.get('event', '')
        data = payload.get('data', {})

        logger.info(f"Google Workspace webhook received: {event_type}")

        if event_type == 'file.uploaded':
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
