"""
Asynchronous service for plan document upload and processing.

Handles direct‑to‑GCS upload and RabbitMQ message publishing.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

import aio_pika
from google.cloud import storage
from google.cloud.storage import Blob, Client

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvidenceProcessor:
    """
    Service to accept file bytes, upload to GCS, and trigger the PlanInspector worker via RabbitMQ.
    """

    def __init__(self):
        # Initialize GCS client using service account JSON (if provided)
        self.storage_client: Client
        if settings.GCP_CREDENTIALS_JSON:
            self.storage_client = storage.Client.from_service_account_json(
                settings.GCP_CREDENTIALS_JSON, project=settings.GCP_PROJECT
            )
        else:
            # Fallback to default credentials (e.g., from environment)
            self.storage_client = storage.Client(project=settings.GCP_PROJECT)

        self.bucket_name = settings.GCS_BUCKET_PLANS
        self._rabbitmq_connection: Optional[aio_pika.Connection] = None
        self._rabbitmq_channel: Optional[aio_pika.Channel] = None

    async def _ensure_rabbitmq(self):
        """Lazy initialisation of RabbitMQ connection and channel."""
        if self._rabbitmq_connection is None or self._rabbitmq_connection.is_closed:
            self._rabbitmq_connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URI
            )
            self._rabbitmq_channel = await self._rabbitmq_connection.channel()
            # Declare exchange
            await self._rabbitmq_channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

    async def process_upload(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload file bytes to GCS and publish a processing message to RabbitMQ.

        Args:
            file_bytes: Raw file content.
            filename: Original filename (used to infer extension).

        Returns:
            Dict containing upload status and GCS object details.
        """
        # Generate a unique object name
        object_name = f"plans/{uuid.uuid4()}_{filename}"
        bucket = self.storage_client.bucket(self.bucket_name)
        blob: Blob = bucket.blob(object_name)

        # Upload in a thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                blob.upload_from_string,
                file_bytes,
                content_type="application/pdf",  # assume PDF, but can be generalised
            )
        except Exception as e:
            logger.exception("GCS upload failed")
            raise RuntimeError(f"Failed to upload to GCS: {e}")

        # Prepare metadata for RabbitMQ
        message_payload = {
            "object_name": object_name,
            "bucket": self.bucket_name,
            "original_filename": filename,
            "timestamp": None,  # will be set by worker
        }

        # Publish to RabbitMQ
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
