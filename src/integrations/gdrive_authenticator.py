#!/usr/bin/env python3
"""
Google Drive Authentication Module for CAIS Acquisitor.
Provides secure, read-only access to Google Drive.
"""

import os
import json
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GDriveAuthenticator:
    """
    Authenticates with Google Drive using a service account.
    Provides read-only access for document acquisition.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the authenticator.

        Args:
            credentials_path: Path to the service account JSON key file.
                           If None, uses default path.
        """
        self.credentials_path = credentials_path or \
            os.path.expanduser("~/PROMETHEUS/config/security/gdrive-credentials.json")

        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found at {self.credentials_path}. "
                "Please place your service account key there and set permissions to 600."
            )

        self._service = None

    def authenticate(self):
        """
        Authenticate and build the Drive service object.

        Returns:
            Google Drive service object.
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )

            self._service = build('drive', 'v3', credentials=credentials)
            return self._service

        except Exception as e:
            raise RuntimeError(f"Failed to authenticate with Google Drive: {e}")

    def get_service(self):
        """
        Get the Drive service object, authenticating if necessary.

        Returns:
            Google Drive service object.
        """
        if not self._service:
            self.authenticate()
        return self._service

    def test_connection(self) -> bool:
        """
        Test the connection to Google Drive.

        Returns:
            bool: True if connection is successful.
        """
        try:
            service = self.get_service()
            service.files().list(pageSize=1).execute()
            return True
        except HttpError as e:
            print(f"Connection test failed: {e}")
            return False
