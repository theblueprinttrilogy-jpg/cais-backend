"""
Asynchronous service for plan document upload and processing.

Handles direct-to-GCS upload and RabbitMQ message publishing.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

import aio_pika
from google.oauth2 import service_account
from google.cloud import storage
from google.cloud.storage import Blob, Client

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvidenceProcessor:
    """
    Service to accept file bytes, upload to GCS, and trigger the PlanInspector worker via RabbitMQ.
    """

    def __init__(self):
        # Initialize GCS client using service account JSON or fallback
        self.storage_client: Client = self._create_storage_client()
        self.bucket_name = settings.GCS_BUCKET_PLANS
        self._rabbitmq_connection: Optional[aio_pika.Connection] = None
        self._rabbitmq_channel: Optional[aio_pika.Channel] = None

    def _create_storage_client(self) -> Client:
        if hasattr(settings, "GCP_CREDENTIALS_JSON") and settings.GCP_CREDENTIALS_JSON:
            creds_json = settings.GCP_CREDENTIALS_JSON
            try:
                if os.path.exists(creds_json):
                    with open(creds_json, "r") as f:
                        info = json.load(f)
                else:
                    info = json.loads(creds_json)

                credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                return storage.Client(project=settings.GCP_PROJECT, credentials=credentials)
            except Exception as e:
                logger.warning("Failed to load service account credentials, falling back to default: %s", e)
        
        return storage.Client(project=settings.GCP_PROJECT)

    async def _ensure_rabbitmq(self):
        """Lazy initialisation of RabbitMQ connection and channel."""
        if self._rabbitmq_connection is None or self._rabbitmq_connection.is_closed:
            self._rabbitmq_connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URI
            )
            self._rabbitmq_channel = await self._rabbitmq_connection.channel()
            await self._rabbitmq_channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

    async def process_upload(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload file bytes to GCS and publish a processing message to RabbitMQ.
        """
        object_name = f"plans/{uuid.uuid4()}_{filename}"
        bucket = self.storage_client.bucket(self.bucket_name)
        blob: Blob = bucket.blob(object_name)

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                blob.upload_from_string,
                file_bytes,
                content_type="application/pdf",
            )
        except Exception as e:
            logger.exception("GCS upload failed")
            raise RuntimeError(f"Failed to upload to GCS: {e}")

        message_payload = {
            "object_name": object_name,
            "bucket": self.bucket_name,
            "original_filename": filename,
            "timestamp": None,
        }

        await self._publish_processing_message(message_payload)

        return {
            "status": "uploaded",
            "object_name": object_name,
            "bucket": self.bucket_name,
        }

    async def _publish_processing_message(self, payload: Dict[str, Any]) -> None:
        """Publish a message to the plan processing exchange."""
        await self._ensure_rabbitmq()

        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self._rabbitmq_channel.default_exchange.publish(
            message,
            routing_key=settings.RABBITMQ_ROUTING_KEY,
        )
        logger.info("Published processing message for object: %s", payload.get("object_name"))

    async def close(self) -> None:
        """Gracefully close RabbitMQ connection."""
        if self._rabbitmq_connection and not self._rabbitmq_connection.is_closed:
            await self._rabbitmq_connection.close()
            self._rabbitmq_connection = None
            self._rabbitmq_channel = None


# Singleton instance
evidence_processor = EvidenceProcessor()
