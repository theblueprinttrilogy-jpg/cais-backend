# Database configuration for CAIS Backend

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cais_user:cais_password@localhost:5432/cais_db")

engine = create_engine(
    DATABASE_URL,
    pool_size=int(os.environ.get("DB_POOL_SIZE", 20)),
    max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", 40)),
    pool_timeout=int(os.environ.get("DB_POOL_TIMEOUT", 60)),
    pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", 3600)),
    pool_pre_ping=True,
    echo=os.environ.get("DB_ECHO", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)
Base = declarative_base()

def get_db_session():
    return db_session()

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_engine():
    return engine

def close_db_session():
    db_session.remove()
