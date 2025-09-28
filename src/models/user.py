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

    active_database_connections = Column(Integer, ForeignKey("database_connections.id"))
    active_model_connections = Column(Integer, ForeignKey("model_connections.id"))
    active_db_schemas = Column(Integer, ForeignKey("db_schemas.id"))

    # 关联模型连接，一对多
    model_connections = relationship("ModelConnection", back_populates="user", foreign_keys="ModelConnection.user_id")
    # 关联数据库连接，一对多
    database_connections = relationship("DatabaseConnection", back_populates="user", foreign_keys="DatabaseConnection.user_id")
    # 关联数据库模式，一对多
    db_schemas = relationship("DbSchema", back_populates="user", foreign_keys="DbSchema.user_id")