from src.models.base import Base
from src.db.registry import DatabaseRegistry
import logging

logger = logging.getLogger(__name__)

# Global service registry instance (will be initialized with default SQLite)
service_db = DatabaseRegistry()


def configure_service_db(database_url: str) -> None:
    """Configure the global database registry with a specific URL."""
    global service_db
    service_db = DatabaseRegistry(database_url)
    logger.info(f"Database configured with URL: {database_url}")


def migrate_service_db(Base, force: bool = False) -> None:
    """Migrate database tables using the global registry.
    
    Args:
        Base: SQLAlchemy Base class containing table metadata
        force: If True, recreate tables even if they exist
    """
    service_db.migrate(Base, force)


async def migrate_service_db_async(Base, force: bool = False) -> None:
    """Migrate database tables using the global registry (async version).
    
    Args:
        Base: SQLAlchemy Base class containing table metadata
        force: If True, recreate tables even if they exist
    """
    await service_db.migrate_async(Base, force)


def get_service_db():
    """Get a database session context manager."""
    return service_db.session()


async def get_service_db_async():
    """Get an async database session."""
    async with service_db.async_session() as session:
        yield session