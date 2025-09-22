from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class DatabaseConnection(Base):
    """
    数据库连接信息
    一个用户可能会配置多个数据库
    """
    __tablename__ = "database_connections"
    id = Column(Integer, primary_key=True, index=True)
    database_name = Column(String, unique=True, index=True) # 用户自定义的数据库名称

    database_uri = Column(String) # 数据库 URI
    
    database_type = Column(String)              # 数据库类型
    database_description = Column(String, default="") # 数据库描述
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 外键关联用户
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="database_connections")
    active_database_connections = relationship("ActiveDatabaseConnection", back_populates="database_connection")


class ActiveDatabaseConnection(Base):
    """
    活跃数据库连接信息
    """
    __tablename__ = "active_database_connections"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    database_connection_id = Column(Integer, ForeignKey("database_connections.id"))
    
    user = relationship("User", back_populates="active_database_connections")
    database_connection = relationship("DatabaseConnection", back_populates="active_database_connections")

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())