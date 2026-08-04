import asyncio
import logging
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.code_reference import CodeReference

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize the embedding model
MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> List[float]:
    """
    Generate a normalized embedding vector for the given text.
    """
    return embedding_model.encode(text, normalize_embeddings=True).tolist()


# Sample code reference data (construction and fire safety regulations)
SAMPLE_CODES: List[Dict[str, Any]] = [
    {
        "jurisdiction": "US-FL",
        "code_type": "fire",
        "section": "NFPA 101.3.1",
        "title": "Means of Egress",
        "description": "Every building must have at least two separate means of egress from each floor.",
        "full_text": "NFPA 101 Life Safety Code, Chapter 3: Means of Egress. Section 3.1 requires that every occupied space have at least two exits that are remote from each other and accessible without traversing a high-hazard area.",
        "severity": "critical",
    },
    {
        "jurisdiction": "US-FL",
        "code_type": "building",
        "section": "FBC 1004.1",
        "title": "Occupant Load Determination",
        "description": "The occupant load for a building space is determined by dividing the floor area by the occupant load factor.",
        "full_text": "Florida Building Code, Section 1004.1: The occupant load for each space shall be determined based on the function of the space and the area per occupant as provided in Table 1004.5. The calculation must include all portions of the building.",
        "severity": "warning",
    },
    {
        "jurisdiction": "US-FL",
        "code_type": "fire",
        "section": "NFPA 13.2.1",
        "title": "Sprinkler System Requirements",
        "description": "Automatic sprinkler systems are required in all new buildings exceeding a certain area or height.",
        "full_text": "NFPA 13 Standard for the Installation of Sprinkler Systems, Chapter 2: General Requirements. Section 2.1 mandates that automatic sprinkler protection be provided in buildings with a floor area exceeding 5,000 square feet or greater than two stories.",
        "severity": "critical",
    },
]


async def seed_codes() -> None:
    """
    Seed the code_references table with sample data.
    Idempotently skips sections that already exist.
    """
    logger.info("Starting code references seeding...")

    async with async_session_factory() as session:
        # Check existing sections to avoid duplicates
        existing_sections = set()
        stmt = select(CodeReference.section, CodeReference.jurisdiction, CodeReference.code_type)
        result = await session.execute(stmt)
        for row in result.all():
            # row is a tuple (section, jurisdiction, code_type)
            key = (row[0], row[1], row[2])
            existing_sections.add(key)

        inserted = 0
        skipped = 0

        for code_data in SAMPLE_CODES:
            section = code_data["section"]
            jurisdiction = code_data["jurisdiction"]
            code_type = code_data["code_type"]

            # Check if this exact combination already exists
            if (section, jurisdiction, code_type) in existing_sections:
                logger.info(f"Skipping existing: {section} ({jurisdiction}, {code_type})")
                skipped += 1
                continue

            # Generate embedding from full_text if available, else from description+title
            text_to_embed = code_data.get("full_text") or f"{code_data['title']} {code_data['description']}"
            embedding_vector = generate_embedding(text_to_embed)

            # Create CodeReference instance
            ref = CodeReference(
                jurisdiction=jurisdiction,
                code_type=code_type,
                section=section,
                title=code_data.get("title"),
                description=code_data.get("description"),
                full_text=code_data.get("full_text"),
                severity=code_data.get("severity"),
                embedding=embedding_vector,
            )
            session.add(ref)
            inserted += 1
            logger.info(f"Inserted: {section} ({jurisdiction}, {code_type})")

        await session.commit()
        logger.info(f"Seeding completed. Inserted {inserted} new records, skipped {skipped} existing.")


async def main() -> None:
    """
    Main entry point for the seeding script.
    """
    try:
        await seed_codes()
    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
