"""
Database configuration and session management.

Uses SQLAlchemy 2.0+ with asyncpg for asynchronous database operations.
Connects to Google Cloud SQL PostgreSQL instance.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Create async engine
def create_engine() -> AsyncEngine:
    """
    Create async database engine with appropriate configuration.

    Returns:
        AsyncEngine configured for Cloud SQL connection
    """
    engine_kwargs: dict[str, Any] = {
        "echo": settings.DEBUG,
        "future": True,
    }

    # Connection pool configuration
    if settings.is_production:
        # Production: Use Unix socket for Cloud SQL
        # Async engine uses its own async pool adapter
        engine_kwargs.update({
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,  # Verify connections before using
        })
    else:
        # Development: Via Cloud SQL Proxy
        engine_kwargs.update({
            "pool_size": 2,
            "max_overflow": 5,
            "pool_pre_ping": True,
        })

    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


# Create engine instance
engine = create_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.

    Yields:
        AsyncSession: Database session that will be automatically closed

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.

    Note: In production, use Alembic migrations instead.
    This is useful for testing and development only.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database engine and dispose of connection pool."""
    await engine.dispose()


async def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
