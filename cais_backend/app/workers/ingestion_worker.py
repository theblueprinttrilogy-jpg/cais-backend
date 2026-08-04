import asyncio
import io
import logging
import os
import signal
from typing import List, Dict, Any, Optional

import PyPDF2
from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.code_reference import CodeReference
from app.services.drive import GoogleDriveUploader

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_ROOT_FOLDER_ID = "16ywo8njoZ4l7GYKBF1z9CPYQukrmqGVr"
DEFAULT_CREDENTIALS_PATH = "app/credentials/service-account.json"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_JURISDICTION = "US-FL"
DEFAULT_CODE_TYPE = "building"


class IngestionWorker:
    """
    Worker that periodically fetches PDF documents from a Google Drive folder,
    extracts text, generates embeddings, and stores them in the code_references
    table. Runs asynchronously and supports graceful shutdown.
    """

    def __init__(
        self,
        interval_seconds: int = 60,
        credentials_path: Optional[str] = None,
        root_folder_id: Optional[str] = None,
        jurisdiction: str = DEFAULT_JURISDICTION,
        code_type: str = DEFAULT_CODE_TYPE,
    ) -> None:
        """
        Initialize the ingestion worker.

        :param interval_seconds: Time between ingestion cycles.
        :param credentials_path: Path to Google Drive service account credentials.
        :param root_folder_id: ID of the Google Drive folder containing PDFs.
        :param jurisdiction: Default jurisdiction for ingested codes.
        :param code_type: Default code type for ingested codes.
        """
        self.interval_seconds = interval_seconds
        self.credentials_path = credentials_path or DEFAULT_CREDENTIALS_PATH
        self.root_folder_id = root_folder_id or DEFAULT_ROOT_FOLDER_ID
        self.jurisdiction = jurisdiction
        self.code_type = code_type
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Initialize embedding model once (synchronous, but we can load in thread)
        # We'll load it lazily in the first cycle to avoid blocking the constructor.
        self.embedding_model: Optional[SentenceTransformer] = None

    def _load_embedding_model(self) -> None:
        """Load the SentenceTransformer model (blocking, called in thread)."""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from a PDF binary content.
        This is a blocking I/O operation, so it should be run in a thread.

        :param pdf_bytes: Raw PDF file content.
        :return: Extracted text as a single string.
        """
        with io.BytesIO(pdf_bytes) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts).strip()

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate a normalized embedding vector for the given text.
        This is a CPU-bound operation, so it should be run in a thread.

        :param text: Input text.
        :return: List of floats (384-dimensional).
        """
        if self.embedding_model is None:
            self._load_embedding_model()
        return self.embedding_model.encode(text, normalize_embeddings=True).tolist()

    def _create_drive_service(self) -> GoogleDriveUploader:
        """
        Create a GoogleDriveUploader instance (blocking constructor).
        """
        return GoogleDriveUploader(credentials_path=self.credentials_path)

    async def _process_pdf(
        self,
        file_id: str,
        file_name: str,
        drive_service: GoogleDriveUploader,
    ) -> Optional[CodeReference]:
        """
        Download a PDF from Drive, extract text, generate embedding,
        and prepare a CodeReference instance if the text is not empty.

        :param file_id: Google Drive file ID.
        :param file_name: Name of the file.
        :param drive_service: GoogleDriveUploader instance.
        :return: CodeReference instance or None if extraction failed.
        """
        try:
            logger.debug(f"Processing file: {file_name} (ID: {file_id})")
            # Download file content (blocking, run in thread)
            file_content = await asyncio.to_thread(drive_service.download_file, file_id)
            if not file_content:
                logger.warning(f"Empty content for {file_name}")
                return None

            # Extract text (blocking)
            text = await asyncio.to_thread(self._extract_text_from_pdf, file_content)
            if not text:
                logger.warning(f"No text extracted from {file_name}")
                return None

            # Generate embedding (blocking)
            embedding_vector = await asyncio.to_thread(self._generate_embedding, text)

            # Derive section from file name (remove extension)
            section = os.path.splitext(file_name)[0]
            # Truncate to 100 characters max for the column
            section = section[:100]

            # Create a CodeReference instance
            code_ref = CodeReference(
                jurisdiction=self.jurisdiction,
                code_type=self.code_type,
                section=section,
                title=file_name,
                description=text[:500],  # Truncated description
                full_text=text,
                severity="warning",  # Default severity
                embedding=embedding_vector,
            )
            return code_ref
        except Exception as e:
            logger.error(f"Failed to process PDF {file_name}: {e}", exc_info=True)
            return None

    async def _upsert_code_reference(self, code_ref: CodeReference) -> bool:
        """
        Insert or update a CodeReference record in the database.
        Checks for existing record based on jurisdiction, code_type, section.
        If exists, updates the fields; otherwise inserts.

        :param code_ref: CodeReference instance.
        :return: True if successful, False otherwise.
        """
        async with async_session_factory() as session:
            try:
                # Check for existing record
                stmt = select(CodeReference).where(
                    CodeReference.jurisdiction == code_ref.jurisdiction,
                    CodeReference.code_type == code_ref.code_type,
                    CodeReference.section == code_ref.section,
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing record
                    existing.title = code_ref.title
                    existing.description = code_ref.description
                    existing.full_text = code_ref.full_text
                    existing.severity = code_ref.severity
                    existing.embedding = code_ref.embedding
                    logger.debug(f"Updated existing record for {code_ref.section}")
                else:
                    # Insert new record
                    session.add(code_ref)
                    logger.debug(f"Inserted new record for {code_ref.section}")

                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"Database error upserting {code_ref.section}: {e}", exc_info=True)
                return False

    async def _ingest_cycle(self) -> None:
        """
        Execute a single ingestion cycle: fetch PDFs from Drive, process them,
        and store/update in the database.
        """
        logger.info("Starting ingestion cycle")

        # Create Drive service (blocking, run in thread)
        drive_service = await asyncio.to_thread(self._create_drive_service)

        try:
            # List all PDF files in the root folder using the query
            query = f"'{self.root_folder_id}' in parents and mimeType='application/pdf'"
            # list_files is blocking, run in thread
            response = await asyncio.to_thread(drive_service.list_files, query=query)

            # The response is a dictionary with a "files" key
            files_metadata = response.get("files", [])
            logger.info(f"Found {len(files_metadata)} PDF files in Drive")

            if not files_metadata:
                logger.info("No PDF files to process")
                return

            processed = 0
            successful = 0

            for file_info in files_metadata:
                file_id = file_info.get("id")
                file_name = file_info.get("name")
                if not file_id or not file_name:
                    logger.warning(f"Skipping file with missing id or name: {file_info}")
                    continue

                code_ref = await self._process_pdf(file_id, file_name, drive_service)
                if code_ref:
                    processed += 1
                    if await self._upsert_code_reference(code_ref):
                        successful += 1

            logger.info(
                f"Ingestion cycle completed: processed {processed} PDFs, "
                f"successfully upserted {successful} records."
            )
        except Exception as e:
            logger.error(f"Ingestion cycle failed: {e}", exc_info=True)
        finally:
            # Clean up drive service if it has a close method (no-op currently)
            if hasattr(drive_service, "close"):
                if asyncio.iscoroutinefunction(drive_service.close):
                    await drive_service.close()
                else:
                    await asyncio.to_thread(drive_service.close)

    async def start(self) -> None:
        """
        Start the worker loop.
        """
        if self._running:
            logger.warning("Worker is already running")
            return

        self._running = True
        logger.info(f"Starting ingestion worker with interval {self.interval_seconds}s")

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        while self._running:
            try:
                await self._ingest_cycle()
            except asyncio.CancelledError:
                logger.info("Ingestion cycle cancelled")
                break
            except Exception as e:
                logger.error(f"Unhandled error in ingestion cycle: {e}", exc_info=True)

            if self._running:
                logger.debug(f"Sleeping for {self.interval_seconds} seconds")
                await asyncio.sleep(self.interval_seconds)

        logger.info("Ingestion worker stopped")

    async def stop(self) -> None:
        """
        Signal the worker to stop after the current cycle.
        """
        logger.info("Stopping ingestion worker...")
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


async def main() -> None:
    """
    Entry point for the ingestion worker.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Override from environment if present
    interval = int(os.getenv("INGESTION_INTERVAL", "60"))
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", DEFAULT_CREDENTIALS_PATH)
    folder_id = os.getenv("DRIVE_ROOT_FOLDER_ID", DEFAULT_ROOT_FOLDER_ID)
    jurisdiction = os.getenv("DEFAULT_JURISDICTION", DEFAULT_JURISDICTION)
    code_type = os.getenv("DEFAULT_CODE_TYPE", DEFAULT_CODE_TYPE)

    worker = IngestionWorker(
        interval_seconds=interval,
        credentials_path=credentials,
        root_folder_id=folder_id,
        jurisdiction=jurisdiction,
        code_type=code_type,
    )
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
