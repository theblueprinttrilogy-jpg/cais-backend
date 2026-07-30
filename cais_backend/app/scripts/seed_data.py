"""
Seed Data Script - Populates Database with Initial Data

This script populates the database with initial code references and test data.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import CodeReference, User
from app.core.config import settings
from app.core.jwt import get_password_hash

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def seed_database():
    """
    Seed the database with initial data.
    """
    DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    logger.info(f"Connecting to database: {DATABASE_URL}")

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if codes already exist
        existing_codes = db.query(CodeReference).count()
        if existing_codes > 0:
            logger.info(f"Codes already exist ({existing_codes} records). Skipping seed.")
        else:
            logger.info("Seeding code references...")

            # IBC Codes
            ibc_codes = [
                {
                    "code_type": "IBC",
                    "section": "1005.3.1",
                    "title": "Means of Egress Door Width",
                    "description": "Minimum door width for means of egress shall be 32 inches (813 mm).",
                    "full_text": "1005.3.1 Door Width. The minimum width of each door opening shall be 32 inches (813 mm).",
                    "jurisdiction": "International",
                    "severity": "Critical"
                },
                {
                    "code_type": "IBC",
                    "section": "1007",
                    "title": "Means of Egress for Fire Safety",
                    "description": "Means of egress requirements for fire safety.",
                    "full_text": "1007 Means of Egress. The means of egress shall be designed and maintained to provide a safe path of travel for occupants during an emergency.",
                    "jurisdiction": "International",
                    "severity": "Critical"
                },
                {
                    "code_type": "IBC",
                    "section": "1004",
                    "title": "Occupant Load",
                    "description": "Occupant load requirements.",
                    "full_text": "1004 Occupant Load. The occupant load shall be determined based on the use of the space.",
                    "jurisdiction": "International",
                    "severity": "High"
                },
                {
                    "code_type": "IBC",
                    "section": "1604.4",
                    "title": "Structural Integrity",
                    "description": "Structures shall be designed to resist all applicable loads.",
                    "full_text": "1604.4 Structural Integrity. Structures shall be designed to resist all applicable loads.",
                    "jurisdiction": "International",
                    "severity": "High"
                },
                {
                    "code_type": "IBC",
                    "section": "1803.5",
                    "title": "Foundation Requirements",
                    "description": "Foundation design and construction requirements.",
                    "full_text": "1803.5 Foundation Requirements. Foundations shall be designed and constructed to support the structure.",
                    "jurisdiction": "International",
                    "severity": "High"
                },
                {
                    "code_type": "IBC",
                    "section": "1006.2.1",
                    "title": "Egress Width Requirements",
                    "description": "Minimum egress width requirements.",
                    "full_text": "1006.2.1 Egress Width. Minimum egress width shall be 32 inches (813 mm).",
                    "jurisdiction": "International",
                    "severity": "Critical"
                }
            ]

            for code_data in ibc_codes:
                code = CodeReference(**code_data)
                db.add(code)
            db.commit()
            logger.info(f"Seeded {len(ibc_codes)} IBC codes")

            # NFPA Codes
            nfpa_codes = [
                {
                    "code_type": "NFPA",
                    "section": "NFPA 101",
                    "title": "Life Safety Code",
                    "description": "Requirements for life safety in buildings.",
                    "full_text": "NFPA 101 Life Safety Code. Requirements for life safety in buildings.",
                    "jurisdiction": "International",
                    "severity": "Critical"
                },
                {
                    "code_type": "NFPA",
                    "section": "NFPA 13",
                    "title": "Sprinkler Systems",
                    "description": "Requirements for fire sprinkler systems.",
                    "full_text": "NFPA 13 Sprinkler Systems. Requirements for fire sprinkler systems.",
                    "jurisdiction": "International",
                    "severity": "High"
                },
                {
                    "code_type": "NFPA",
                    "section": "NFPA 70",
                    "title": "National Electrical Code",
                    "description": "Requirements for electrical systems.",
                    "full_text": "NFPA 70 National Electrical Code. Requirements for electrical systems.",
                    "jurisdiction": "International",
                    "severity": "High"
                }
            ]

            for code_data in nfpa_codes:
                code = CodeReference(**code_data)
                db.add(code)
            db.commit()
            logger.info(f"Seeded {len(nfpa_codes)} NFPA codes")

            # OSHA Codes
            osha_codes = [
                {
                    "code_type": "OSHA",
                    "section": "1926.20",
                    "title": "Safety and Health Programs",
                    "description": "Requirements for safety and health programs.",
                    "full_text": "1926.20 Safety and Health Programs. Requirements for safety and health programs.",
                    "jurisdiction": "US",
                    "severity": "High"
                },
                {
                    "code_type": "OSHA",
                    "section": "1926.21",
                    "title": "Safety Training",
                    "description": "Requirements for safety training.",
                    "full_text": "1926.21 Safety Training. Requirements for safety training.",
                    "jurisdiction": "US",
                    "severity": "Medium"
                }
            ]

            for code_data in osha_codes:
                code = CodeReference(**code_data)
                db.add(code)
            db.commit()
            logger.info(f"Seeded {len(osha_codes)} OSHA codes")

            # ADA Codes
            ada_codes = [
                {
                    "code_type": "ADA",
                    "section": "ADA-001",
                    "title": "Americans with Disabilities Act",
                    "description": "Requirements for accessibility.",
                    "full_text": "ADA Americans with Disabilities Act. Requirements for accessibility.",
                    "jurisdiction": "US",
                    "severity": "Critical"
                }
            ]

            for code_data in ada_codes:
                code = CodeReference(**code_data)
                db.add(code)
            db.commit()
            logger.info(f"Seeded {len(ada_codes)} ADA codes")

        # Create admin user if not exists
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@cais.com")
        admin_user = db.query(User).filter(User.email == admin_email).first()

        if not admin_user:
            logger.info("Creating admin user...")
            admin_user = User(
                email=admin_email,
                username="admin",
                hashed_password=get_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123!")),
                full_name="CAIS Admin",
                is_active=True,
                is_superuser=True,
                is_verified=True,
                preferred_language="en"
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"Admin user created: {admin_email}")
        else:
            logger.info(f"Admin user already exists: {admin_email}")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    logger.info("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
