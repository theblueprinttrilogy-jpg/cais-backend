"""
Asynchronous database session management for the CAIS backend.

Provides an async engine, session factory, and dependency for FastAPI endpoints.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# Create async engine with pool pre-ping to detect stale connections
engine = create_async_engine(
    settings.POSTGRES_DSN,
    pool_pre_ping=True,
    echo=False,  # set to True for debugging
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency that yields a database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
