from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.config import get_settings
from contextlib import contextmanager
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

settings = get_settings()

def ensure_db_setup():
    """确保数据库文件和目录正确创建"""
    try:
        # 1. 确保目录存在
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 2. 检查权限
        if not os.access(db_path.parent, os.W_OK):
            raise PermissionError(f"No write permission: {db_path.parent}")
        
        logger.info(f"Database setup complete: {db_path.absolute()}")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(
    DATABASE_URL,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info(f"Database connected")

Base = declarative_base()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    from src.api.model import User, ModelConnection, DatabaseConnection
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info(f"Database tables created")