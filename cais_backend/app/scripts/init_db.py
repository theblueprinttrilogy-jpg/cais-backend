"""
Database Initialization Script

This script initializes the database with all tables and extensions.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
from app.db.models import Base
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize the database with all tables and extensions.
    """
    DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    logger.info(f"Connecting to database: {DATABASE_URL}")

    # Create engine
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600
    )

    # Create all tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")

    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        logger.info("pgvector extension enabled")

    # Create indexes for performance
    with engine.connect() as conn:
        logger.info("Creating indexes...")

        # User indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_subscription_plan ON users(subscription_plan);"))

        # Project indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);"))

        # Document indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);"))

        # Violation indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_violations_document_id ON violations(document_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_violations_severity ON violations(severity);"))

        # Code Reference indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_codes_code_type ON code_references(code_type);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_codes_jurisdiction ON code_references(jurisdiction);"))

        # Payment indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);"))

        # WORM Ledger indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_worm_timestamp ON worm_ledger(timestamp);"))

        conn.commit()
        logger.info("Indexes created successfully")

    logger.info("Database initialization completed successfully!")


if __name__ == "__main__":
    init_database()
