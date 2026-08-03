"""
Batch ingestion script for large-scale legal building code corpora.

This script reads a JSON file containing legal provisions (IBC, FBC, local amendments),
generates vector embeddings using SentenceTransformer, and upserts them into the
CAIS PostgreSQL database with pgvector.

Supports multi-jurisdictional state, county, and municipal codes across US territories.
"""

import asyncio
import argparse
import json
import logging
import sys
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from sentence_transformers import SentenceTransformer

from app.db.session import AsyncSessionLocal
from app.db.models import CodeReference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_records_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load code records from a JSON file.

    Expected JSON format: a list of objects with fields:
        code_type, section, title, description, full_text, jurisdiction, severity

    Args:
        file_path: Path to the JSON file.

    Returns:
        List of record dictionaries.

    Raises:
        FileNotFoundError, json.JSONDecodeError
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of records.")

    required_fields = {"code_type", "section", "title", "description",
                       "full_text", "jurisdiction", "severity"}
    for idx, record in enumerate(data):
        missing = required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Record {idx} missing fields: {missing}")

    return data


def get_embedding_model() -> SentenceTransformer:
    """Initialize and return the sentence transformer model."""
    logger.info("Loading sentence transformer model 'all-MiniLM-L6-v2' ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Model loaded successfully.")
    return model


def chunk_list(lst: List[Any], chunk_size: int):
    """Yield successive chunks of a list."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


async def upsert_records_batch(
    session: AsyncSessionLocal,
    records: List[Dict[str, Any]],
    model: SentenceTransformer
) -> Tuple[int, int, int]:
    """
    Upsert a batch of records: generate embeddings, detect duplicates, insert/update.

    Returns:
        Tuple of (inserted_count, updated_count, skipped_count)
    """
    if not records:
        return 0, 0, 0

    # Batch encode all full_texts at once
    texts = [rec["full_text"] for rec in records]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    # Build composite key for each record: (code_type, section, jurisdiction)
    key_to_record = {}
    for idx, rec in enumerate(records):
        key = (rec["code_type"], rec["section"], rec["jurisdiction"])
        key_to_record[key] = {
            "record": rec,
            "embedding": embeddings[idx].tolist()
        }

    # Fetch existing records that match any of the keys
    stmt = select(CodeReference).where(
        and_(
            CodeReference.code_type.in_([r["code_type"] for r in records]),
            CodeReference.section.in_([r["section"] for r in records]),
            CodeReference.jurisdiction.in_([r["jurisdiction"] for r in records])
        )
    )
    # Note: This simple multi-column IN clause might be inefficient for large batches.
    # For true production, we would use a tuple comparison or a temp table.
    # For our purpose, we fetch all and filter in Python.
    result = await session.execute(stmt)
    existing_refs = result.scalars().all()

    # Build a map of existing records by composite key
    existing_map = {}
    for ref in existing_refs:
        key = (ref.code_type, ref.section, ref.jurisdiction)
        existing_map[key] = ref

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    for key, data in key_to_record.items():
        rec = data["record"]
        embedding = data["embedding"]
        existing = existing_map.get(key)

        if existing:
            # Check if full_text differs
            if existing.full_text != rec["full_text"]:
                # Update
                existing.title = rec["title"]
                existing.description = rec["description"]
                existing.full_text = rec["full_text"]
                existing.severity = rec["severity"]
                existing.embedding = embedding
                updated_count += 1
                logger.debug(f"Updated: {key}")
            else:
                skipped_count += 1
                logger.debug(f"Skipped (unchanged): {key}")
        else:
            # Insert new
            new_ref = CodeReference(
                code_type=rec["code_type"],
                section=rec["section"],
                title=rec["title"],
                description=rec["description"],
                full_text=rec["full_text"],
                jurisdiction=rec["jurisdiction"],
                severity=rec["severity"],
                embedding=embedding
            )
            session.add(new_ref)
            inserted_count += 1
            logger.debug(f"Inserted: {key}")

    return inserted_count, updated_count, skipped_count


async def batch_ingest_corpus(
    records: List[Dict[str, Any]],
    batch_size: int = 50,
    dry_run: bool = False
) -> None:
    """
    Ingest a large corpus of records in batches.

    Args:
        records: List of record dictionaries.
        batch_size: Number of records per batch.
        dry_run: If True, only simulate without committing.
    """
    if not records:
        logger.warning("No records provided. Exiting.")
        return

    model = get_embedding_model()
    total_records = len(records)
    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    # Process in chunks
    for batch_idx, batch in enumerate(chunk_list(records, batch_size), start=1):
        logger.info(f"Processing batch {batch_idx}/{ (total_records + batch_size - 1) // batch_size } "
                    f"(size={len(batch)})")

        async with AsyncSessionLocal() as session:
            try:
                # Retry logic with exponential backoff (simplified)
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        inserted, updated, skipped = await upsert_records_batch(
                            session, batch, model
                        )
                        if not dry_run:
                            await session.commit()
                        else:
                            await session.rollback()
                            logger.info(f"DRY RUN: Would commit changes for batch {batch_idx}")

                        total_inserted += inserted
                        total_updated += updated
                        total_skipped += skipped
                        logger.info(
                            f"Batch {batch_idx} result: inserted={inserted}, updated={updated}, skipped={skipped}"
                        )
                        break  # success, exit retry loop

                    except SQLAlchemyError as e:
                        await session.rollback()
                        logger.error(f"Database error on attempt {attempt}/{max_retries}: {e}")
                        if attempt == max_retries:
                            raise
                        # Wait before retry (exponential backoff)
                        await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Unhandled error in batch {batch_idx}: {e}", exc_info=True)
                # Optionally, you could re-raise to stop the entire process
                # For production, you might want to continue and log the failure
                # We'll raise to halt ingestion to avoid partial state
                raise

    logger.info(
        f"Batch ingestion completed. Total: inserted={total_inserted}, "
        f"updated={total_updated}, skipped={total_skipped}"
    )


def main():
    """CLI entry point for batch ingestion."""
    parser = argparse.ArgumentParser(
        description="Batch ingest legal building code corpus into CAIS database."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to JSON file containing code records (list of objects)."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of records per batch (default: 50)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ingestion without committing to the database."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level."
    )
    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        records = load_records_from_file(args.file)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to load records: {e}")
        sys.exit(1)

    logger.info(f"Loaded {len(records)} records from {args.file}")

    asyncio.run(batch_ingest_corpus(
        records=records,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
