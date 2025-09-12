from sqlalchemy import create_engine, declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.config import get_settings
from contextlib import contextmanager

settings = get_settings()

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=1800,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    Base.metadata.create_all(bind=engine)