# agents/storage_agent.py - Storage Agent for CAIS v2.0
# Production-ready agent responsible for packaging successful search results
# into secure tar.gz archives, generating WORM-compatible JSON manifests
# with SHA-256 hashes, and enforcing an ephemeral resource lifecycle
# (complete purge of temporary directories and files after archive creation).

import os
import asyncio
import logging
import hashlib
import shutil
import tarfile
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

import aiofiles
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------------------
class Jurisdiction(BaseModel):
    """Minimal jurisdiction model for storage manifest."""
    code: str = Field(..., description="Two-letter code or abbreviation")
    name: str = Field(..., description="Full name of the jurisdiction")

class StorageManifest(BaseModel):
    """
    WORM-compatible manifest for a stored archive.
    Contains cryptographic hash, jurisdiction list, document count, and timestamp.
    """
    archive_name: str
    archive_hash_sha256: str
    jurisdictions: List[str]  # List of jurisdiction codes included
    total_documents: int
    created_at_utc: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# ------------------------------------------------------------------------------
# StorageAgent Class
# ------------------------------------------------------------------------------
class StorageAgent:
    """
    Storage Agent responsible for:
        - Collecting search results from agents (as lists of document files).
        - Compressing them into a single .tar.gz archive.
        - Computing SHA-256 hash of the archive.
        - Creating a WORM-compatible manifest.
        - Storing both archive and manifest in the output directory.
        - Purging all temporary files and directories immediately after success.
    """

    def __init__(self, output_dir: Union[str, Path], purge_temp: bool = True):
        """
        Initialize the StorageAgent.

        Args:
            output_dir: Directory where archives and manifests will be stored.
            purge_temp: Whether to delete temporary directories after archiving.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.purge_temp = purge_temp
        self.logger = logger.getChild("StorageAgent")
        self.logger.info(f"StorageAgent initialized. Output directory: {self.output_dir}")

    async def _compute_sha256(self, file_path: Path) -> str:
        """
        Compute the SHA-256 hash of a file asynchronously.

        Args:
            file_path: Path to the file.

        Returns:
            Hexadecimal SHA-256 digest.
        """
        sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            # Read in chunks to avoid memory issues
            while chunk := await f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _create_archive(
        self,
        source_dir: Path,
        archive_name: str
    ) -> Path:
        """
        Create a .tar.gz archive from the contents of the source directory.

        Args:
            source_dir: Directory containing files to archive.
            archive_name: Name of the archive (without extension).

        Returns:
            Path to the created archive.
        """
        archive_path = self.output_dir / f"{archive_name}.tar.gz"
        # Use synchronous tarfile in a thread to avoid blocking
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._create_archive_sync,
            source_dir,
            archive_path
        )
        self.logger.info(f"Archive created: {archive_path}")
        return archive_path

    def _create_archive_sync(self, source_dir: Path, archive_path: Path) -> None:
        """Synchronous helper for creating tar.gz archive."""
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_dir, arcname="")

    async def store_batch(
        self,
        batch_id: str,
        jurisdiction_documents: Dict[str, List[Path]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorageManifest:
        """
        Store a batch of jurisdiction documents into a single tar.gz archive
        with a WORM-compatible manifest.

        Args:
            batch_id: Unique identifier for this batch (e.g., timestamp).
            jurisdiction_documents: Mapping of jurisdiction code -> list of document file paths.
            metadata: Optional extra metadata for the manifest.

        Returns:
            StorageManifest containing archive hash and details.

        Raises:
            ValueError: If no documents are provided.
            RuntimeError: If archive creation or hashing fails.
        """
        if not jurisdiction_documents:
            raise ValueError("No jurisdiction documents provided for archiving.")

        # 1. Create a temporary directory to collect all files
        temp_dir = Path(tempfile.mkdtemp(prefix=f"storage_{batch_id}_"))
        self.logger.debug(f"Created temporary directory: {temp_dir}")

        try:
            # 2. Organize files by jurisdiction in the temp directory
            total_docs = 0
            jurisdictions_included = []
            for jur_code, file_paths in jurisdiction_documents.items():
                if not file_paths:
                    continue
                jur_dir = temp_dir / jur_code
                jur_dir.mkdir(exist_ok=True)
                jurisdictions_included.append(jur_code)
                for src_path in file_paths:
                    if not src_path.exists():
                        self.logger.warning(f"Document {src_path} does not exist; skipping.")
                        continue
                    # Copy file to the jurisdiction subdirectory
                    dest_path = jur_dir / src_path.name
                    # Use asyncio to copy (or shutil in thread)
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, shutil.copy2, src_path, dest_path)
                    total_docs += 1

            if total_docs == 0:
                raise ValueError("No valid documents found after filtering.")

            # 3. Create archive
            archive_name = f"jurisdiction_batch_{batch_id}"
            archive_path = await self._create_archive(temp_dir, archive_name)

            # 4. Compute SHA-256 hash of the archive
            archive_hash = await self._compute_sha256(archive_path)

            # 5. Create manifest
            manifest = StorageManifest(
                archive_name=archive_name,
                archive_hash_sha256=archive_hash,
                jurisdictions=jurisdictions_included,
                total_documents=total_docs,
                metadata=metadata or {}
            )

            # 6. Write manifest file
            manifest_path = self.output_dir / f"{archive_name}_manifest.json"
            async with aiofiles.open(manifest_path, 'w') as f:
                await f.write(manifest.json(indent=2))
            self.logger.info(f"Manifest written: {manifest_path}")

            self.logger.info(
                f"Batch {batch_id} stored successfully: "
                f"{len(jurisdictions_included)} jurisdictions, {total_docs} documents, "
                f"hash={archive_hash[:16]}..."
            )
            return manifest

        finally:
            # 7. Ephemeral Resource Lifecycle: purge temporary directory
            if self.purge_temp and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"Purged temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.error(f"Failed to purge temp directory {temp_dir}: {e}")

    async def store_batch_from_results(
        self,
        batch_id: str,
        search_results: List[Any],  # Expect objects with jurisdiction and documents_found
        metadata: Optional[Dict[str, Any]] = None
    ) -> StorageManifest:
        """
        Convenience method to store a batch from a list of search results.
        Each result object must have:
            - .jurisdiction.code (str)
            - .documents_found (List[str])  # paths to documents

        Args:
            batch_id: Unique batch identifier.
            search_results: List of result objects.
            metadata: Optional metadata.

        Returns:
            StorageManifest.
        """
        doc_map = {}
        for result in search_results:
            jur_code = getattr(result.jurisdiction, "code", None)
            if not jur_code:
                continue
            docs = getattr(result, "documents_found", [])
            if docs:
                # Convert string paths to Path objects
                doc_map[jur_code] = [Path(p) for p in docs if p]
        return await self.store_batch(batch_id, doc_map, metadata)

# ------------------------------------------------------------------------------
# Example Usage (if run as script)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    import sys
    logging.basicConfig(level=logging.INFO)

    async def main():
        # Create a storage agent
        agent = StorageAgent("./storage_output")

        # Simulate some documents
        doc_map = {
            "CA": [Path("/tmp/dummy1.pdf"), Path("/tmp/dummy2.xml")],
            "NY": [Path("/tmp/dummy3.json")],
        }
        # Ensure dummy files exist for demonstration
        for paths in doc_map.values():
            for p in paths:
                if not p.exists():
                    with open(p, 'w') as f:
                        f.write("dummy content")

        manifest = await agent.store_batch("20250315_001", doc_map, {"source": "test"})
        print("Manifest:", manifest.json(indent=2))

    asyncio.run(main())

