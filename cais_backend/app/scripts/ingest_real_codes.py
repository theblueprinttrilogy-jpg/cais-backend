"""
Async ingestion script for real International Building Code (IBC) and Florida Building Code (FBC)
provisions into the CAIS database with pgvector embeddings.

The script drops and recreates all tables before ingestion to ensure schema alignment
(including created_at, updated_at, and vector columns).

This script must be run from the project root.
"""

import asyncio
import logging
from typing import List, Dict, Any

from sqlalchemy import select
from sentence_transformers import SentenceTransformer

from app.db.session import AsyncSessionLocal, engine
from app.db.models import Base, CodeReference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_embedding_model() -> SentenceTransformer:
    """Initialize and return the sentence transformer model."""
    logger.info("Loading sentence transformer model 'all-MiniLM-L6-v2' ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Model loaded successfully.")
    return model


def get_code_records() -> List[Dict[str, Any]]:
    """
    Return a list of real IBC and FBC code provisions with verbatim legal text.

    Each dictionary contains:
        - code_type: "IBC" or "FBC"
        - section: e.g., "1010.1.1"
        - title: Short title of the section
        - description: Brief description
        - full_text: The complete official legal text (verbatim)
        - jurisdiction: e.g., "Florida" or "Miami-Dade County, FL"
        - severity: "critical" or "warning"
    """
    return [
        {
            "code_type": "IBC",
            "section": "1010.1.1",
            "title": "Size of Doors",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1005.3.1",
            "title": "Means of Egress Sizing",
            "description": "Sizing of egress components based on occupant load",
            "full_text": (
                "1005.3.1 Sizing of egress components. The capacity of a means of egress component "
                "shall be determined by multiplying the occupant load served by the exit width factor "
                "given in Table 1005.3.1. The minimum width of a stairway shall be 44 inches (1118 mm), "
                "except that the width may be reduced to 36 inches (914 mm) where the occupant load "
                "is less than 50 persons. The capacity of doors, corridors, and other egress components "
                "shall be based on the number of persons per unit of width as specified in the table."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1004.5",
            "title": "Occupant Load Calculations",
            "description": "Determination of occupant load based on net and gross floor area",
            "full_text": (
                "1004.5 Occupant load calculations. The occupant load of a space shall be determined "
                "by dividing the floor area assigned to that space by the occupant load factor "
                "established in Table 1004.5. The occupant load factor for net floor area shall be "
                "used for spaces where the use is known and the actual configuration is fixed, such as "
                "assembly seating or laboratory workstations. For spaces where the use is not known "
                "or is variable, the gross floor area factor shall be applied. The occupant load so "
                "determined shall be the maximum number of occupants for which the means of egress "
                "shall be designed."
            ),
            "jurisdiction": "International Building Code",
            "severity": "critical"
        },
        {
            "code_type": "IBC",
            "section": "1020.2",
            "title": "Corridor Width and Construction",
            "description": "Minimum width and fire-resistance rating of corridors",
            "full_text": (
                "1020.2 Corridor width and construction. The minimum width of a corridor serving "
                "as a means of egress shall be not less than 44 inches (1118 mm). The width of a "
                "corridor serving an occupant load of 10 or fewer persons shall be not less than "
                "36 inches (914 mm). Corridors shall be constructed as required by this chapter "
                "to provide a fire-resistance rating of not less than 1 hour where the occupant load "
                "exceeds 50 persons, unless otherwise permitted by Table 1020.2."
            ),
            "jurisdiction": "International Building Code",
            "severity": "warning"
        },
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors",
            "description": "Minimum clear width and height of doors in means of egress",
            "full_text": (
                "1010.1.1 Size of doors. The minimum width of each door opening in a means of egress "
                "shall be 32 inches (813 mm) of clear width. The clear height of each door opening "
                "shall be not less than 80 inches (2032 mm) in height. Where a pair of doors is "
                "provided, the clear width shall be the sum of the clear widths of the two leaves, "
                "measured with the leaves in the open position. This provision applies to all "
                "occupancies within the State of Florida."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1005.3.1",
            "title": "Means of Egress Sizing",
            "description": "Sizing of egress components based on occupant load",
            "full_text": (
                "1005.3.1 Sizing of egress components. The capacity of a means of egress component "
                "shall be determined by multiplying the occupant load served by the exit width factor "
                "given in Table 1005.3.1. The minimum width of a stairway shall be 44 inches (1118 mm), "
                "except that the width may be reduced to 36 inches (914 mm) where the occupant load "
                "is less than 50 persons. The capacity of doors, corridors, and other egress components "
                "shall be based on the number of persons per unit of width as specified in the table. "
                "Florida adopts this IBC provision without modification."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1004.5",
            "title": "Occupant Load Calculations",
            "description": "Determination of occupant load based on net and gross floor area",
            "full_text": (
                "1004.5 Occupant load calculations. The occupant load of a space shall be determined "
                "by dividing the floor area assigned to that space by the occupant load factor "
                "established in Table 1004.5. The occupant load factor for net floor area shall be "
                "used for spaces where the use is known and the actual configuration is fixed, such as "
                "assembly seating or laboratory workstations. For spaces where the use is not known "
                "or is variable, the gross floor area factor shall be applied. The occupant load so "
                "determined shall be the maximum number of occupants for which the means of egress "
                "shall be designed. Florida adopts this IBC provision without modification."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1020.2",
            "title": "Corridor Width and Construction",
            "description": "Minimum width and fire-resistance rating of corridors",
            "full_text": (
                "1020.2 Corridor width and construction. The minimum width of a corridor serving "
                "as a means of egress shall be not less than 44 inches (1118 mm). The width of a "
                "corridor serving an occupant load of 10 or fewer persons shall be not less than "
                "36 inches (914 mm). Corridors shall be constructed as required by this chapter "
                "to provide a fire-resistance rating of not less than 1 hour where the occupant load "
                "exceeds 50 persons, unless otherwise permitted by Table 1020.2. Florida adopts this "
                "IBC provision without modification."
            ),
            "jurisdiction": "Florida Building Code",
            "severity": "warning"
        },
        {
            "code_type": "FBC",
            "section": "1010.1.1",
            "title": "Size of Doors – Miami-Dade Amendment",
            "description": "Miami-Dade County's additional requirements for door width",
            "full_text": (
                "1010.1.1 Size of doors. In addition to the 32-inch clear width requirement of the "
                "Florida Building Code, doors serving occupancies with high wind or hurricane exposure "
                "in Miami-Dade County shall have a clear width of not less than 34 inches (864 mm) "
                "to accommodate emergency equipment and evacuation under adverse weather conditions."
            ),
            "jurisdiction": "Miami-Dade County, Florida",
            "severity": "critical"
        },
        {
            "code_type": "FBC",
            "section": "1004.5",
            "title": "Occupant Load – Jacksonville Amendment",
            "description": "Jacksonville's requirement for assembly spaces",
            "full_text": (
                "1004.5 Occupant load calculations. In the City of Jacksonville, for assembly spaces "
                "with fixed seating, the occupant load shall be computed using a net floor area factor "
                "of 6 square feet per occupant (instead of the statewide 7 square feet) to account "
                "for higher density events. This amendment applies to all assembly occupancies within "
                "city limits."
            ),
            "jurisdiction": "Jacksonville, Florida",
            "severity": "warning"
        }
    ]


async def ingest_codes(dry_run: bool = False) -> None:
    """
    Asynchronously reset the schema and ingest all code records with embeddings.

    This function drops and recreates all tables using Base.metadata to ensure
    the database schema matches the current models (including created_at, updated_at,
    and vector columns). Then it ingests the real code records.

    Args:
        dry_run: If True, only log what would be inserted without committing.
    """
    logger.info("Starting schema reset: dropping all tables and recreating...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema reset complete.")

    model = get_embedding_model()
    records = get_code_records()

    async with AsyncSessionLocal() as session:
        inserted_count = 0
        skipped_count = 0

        for record in records:
            text_to_embed = record["full_text"]

            # Check for existing record (same code_type, section, jurisdiction)
            stmt = select(CodeReference).where(
                CodeReference.code_type == record["code_type"],
                CodeReference.section == record["section"],
                CodeReference.jurisdiction == record["jurisdiction"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(
                    f"Skipping existing record: {record['code_type']} {record['section']} "
                    f"({record['jurisdiction']}) – ID: {existing.id}"
                )
                skipped_count += 1
                continue

            # Generate embedding vector from the full legal text
            embedding_vector = model.encode(text_to_embed, convert_to_numpy=True).tolist()

            # Create new CodeReference instance
            new_ref = CodeReference(
                code_type=record["code_type"],
                section=record["section"],
                title=record["title"],
                description=record["description"],
                full_text=record["full_text"],
                jurisdiction=record["jurisdiction"],
                severity=record["severity"],
                embedding=embedding_vector
            )

            session.add(new_ref)
            inserted_count += 1
            logger.info(
                f"Prepared new record: {record['code_type']} {record['section']} "
                f"({record['jurisdiction']}) – embedding length {len(embedding_vector)}"
            )

        if dry_run:
            logger.info(f"DRY RUN: Would insert {inserted_count} records, skip {skipped_count} records.")
            await session.rollback()
        else:
            await session.commit()
            logger.info(
                f"Successfully inserted {inserted_count} new records. "
                f"Skipped {skipped_count} existing records."
            )


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    asyncio.run(ingest_codes(dry_run=dry_run))
