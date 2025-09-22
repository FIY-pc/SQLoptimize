import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class DatabaseRegistry:
    """Simplified registry for database connections and sessions."""

    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url
        self._engine: Engine = None
        self._async_engine: AsyncEngine = None
        self._session_factory: sessionmaker = None
        self._async_session_factory: async_sessionmaker = None
        self._initialized = {"sync": False, "async": False}
        self.logger = logging.getLogger(__name__)
    
    def _get_database_url(self) -> str:
        """Get database URL, with fallback to default SQLite."""
        if self._database_url:
            return self._database_url
        
        # Fallback to default SQLite
        from src.config import settings
        return f"sqlite:///{os.path.join(settings.db_path, 'sqlite.db')}"
    
    def _detect_database_type(self, url: str) -> str:
        """Detect database type from URL."""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        if scheme.startswith('sqlite'):
            return 'sqlite'
        elif scheme.startswith('postgresql'):
            return 'postgresql'
        elif scheme.startswith('mysql'):
            return 'mysql'
        else:
            return 'unknown'
    
    def _get_engine_config(self, db_type: str, is_async: bool) -> dict:
        """Get engine configuration based on database type."""
        config = {"echo": False}
        
        if db_type == 'sqlite':
            if is_async:
                config["poolclass"] = None  # NullPool for async SQLite
        elif db_type == 'postgresql':
            if is_async:
                config.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                })
            else:
                config.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                })
        elif db_type == 'mysql':
            if is_async:
                config.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                })
            else:
                config.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                })
        
        return config

    def migrate(self, Base, force: bool = False) -> None:
        """Initialize database tables using the provided Base metadata.
        
        Args:
            Base: SQLAlchemy Base class containing table metadata
            force: If True, recreate tables even if they exist
        """
        self.initialize_sync()
        if not self._engine:
            raise ValueError("Sync database not initialized")
        
        self.logger.info("Starting database migration...")
        
        if force:
            self.logger.warning("Force mode enabled - dropping existing tables")
            Base.metadata.drop_all(bind=self._engine)
        
        Base.metadata.create_all(bind=self._engine)
        self.logger.info("Database migration completed successfully")

    async def migrate_async(self, Base, force: bool = False) -> None:
        """Initialize database tables using the provided Base metadata (async version).
        
        Args:
            Base: SQLAlchemy Base class containing table metadata
            force: If True, recreate tables even if they exist
        """
        self.initialize_async()
        if not self._async_engine:
            raise ValueError("Async database not initialized")
        
        self.logger.info("Starting async database migration...")
        
        if force:
            self.logger.warning("Force mode enabled - dropping existing tables")
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        
        async with self._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.logger.info("Async database migration completed successfully")

    def initialize_sync(self, force: bool = False) -> None:
        """Initialize the synchronous database engine."""
        if self._initialized["sync"] and not force:
            return
        
        from src.models.base import Base
        
        database_url = self._get_database_url()
        db_type = self._detect_database_type(database_url)
        engine_config = self._get_engine_config(db_type, is_async=False)
        
        self.logger.info(f"Creating {db_type} engine: {database_url}")

        self._engine = create_engine(database_url, **engine_config)
        Base.metadata.create_all(bind=self._engine)
        
        self._session_factory = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self._engine
        )
        self._initialized["sync"] = True

    def initialize_async(self, force: bool = False) -> None:
        """Initialize the asynchronous database engine."""
        if self._initialized["async"] and not force:
            return
        
        database_url = self._get_database_url()
        db_type = self._detect_database_type(database_url)
        engine_config = self._get_engine_config(db_type, is_async=True)
        
        # Convert sync URL to async URL if needed
        if db_type == 'sqlite' and not database_url.startswith('sqlite+aiosqlite'):
            database_url = database_url.replace('sqlite://', 'sqlite+aiosqlite://')
        elif db_type == 'postgresql' and not database_url.startswith('postgresql+asyncpg'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
        elif db_type == 'mysql' and not database_url.startswith('mysql+aiomysql'):
            database_url = database_url.replace('mysql://', 'mysql+aiomysql://')
        
        self.logger.info(f"Creating async {db_type} engine: {database_url}")
        
        self._async_engine = create_async_engine(database_url, **engine_config)
        
        self._async_session_factory = async_sessionmaker(
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
            bind=self._async_engine,
            class_=AsyncSession,
        )
        self._initialized["async"] = True


    @contextmanager
    def session(self) -> Generator[Any, None, None]:
        """Context manager for database sessions."""
        self.initialize_sync()
        if not self._session_factory:
            raise ValueError("Sync database not initialized")
        
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for database sessions."""
        self.initialize_async()
        if not self._async_session_factory:
            raise ValueError("Async database not initialized")
        
        session = self._async_session_factory()
        try:
            yield session
        finally:
            await session.close()