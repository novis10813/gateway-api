"""
Database connection and session management for PostgreSQL.

Uses SQLAlchemy async for non-blocking database operations.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import NullPool

from core.config import settings
from models.db_models import Base


class DatabaseManager:
    """
    Manages PostgreSQL database connections using SQLAlchemy async.
    
    Implements singleton pattern to ensure a single connection pool.
    """
    
    _instance: Optional["DatabaseManager"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Create async engine
        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,  # Check connection health
            pool_size=5,
            max_overflow=10,
            # Use NullPool for tests or when connection pooling is external
            poolclass=NullPool if settings.testing else None,
        )
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        self._initialized = True
    
    @property
    def engine(self):
        """Get the SQLAlchemy async engine."""
        return self._engine
    
    async def init_db(self) -> None:
        """
        Initialize database schema.
        
        Creates all tables if they don't exist.
        Should be called on application startup.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """
        Close database connections.
        
        Should be called on application shutdown.
        """
        await self._engine.dispose()
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session as an async context manager.
        
        Usage:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_session(self) -> AsyncSession:
        """
        Get a new session instance.
        
        Caller is responsible for managing the session lifecycle.
        """
        return self._session_factory()


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with db_manager.session() as session:
        yield session
