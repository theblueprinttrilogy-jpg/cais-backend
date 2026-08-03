import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Database URL from environment, with a sensible default for development.
# Example: postgresql+asyncpg://user:pass@localhost/db
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cais")

# Create the asynchronous engine.
# Using NullPool to avoid connection pooling issues in some async contexts,
# but you can replace with AsyncAdaptedQueuePool if needed.
async_engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
    pool_pre_ping=True,
    poolclass=NullPool,
)

# Create the async session factory.
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Optional: dependency for FastAPI to get a session per request.
# This is not required by the spec but can be included for convenience.
async def get_session() -> AsyncSession:
    """
    Dependency that provides an async database session.
    Usage: async def route(db: AsyncSession = Depends(get_session)).
    """
    async with async_session_factory() as session:
        yield session
