from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class DbSchema(Base):
    """
    数据库模式信息
    """
    __tablename__ = "db_schemas"
    id = Column(Integer, primary_key=True, index=True)
    schema_name = Column(String(100), unique=True, index=True)
    schema_content = Column(Text)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="db_schemas", foreign_keys=[user_id])