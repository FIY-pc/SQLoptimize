from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class User(Base):
    """用户信息"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联模型连接，一对多
    model_connections = relationship("ModelConnection", back_populates="user")
    active_database_connections = relationship("ActiveDatabaseConnection", back_populates="user")
    # 关联数据库连接，一对多
    database_connections = relationship("DatabaseConnection", back_populates="user")