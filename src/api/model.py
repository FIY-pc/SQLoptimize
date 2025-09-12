from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.api.database import Base

class User(Base):
    """用户信息"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联模型连接，一对多
    model_connections = relationship("ModelConnection", back_populates="user")

    # 关联数据库连接，一对多
    database_connections = relationship("DatabaseConnection", back_populates="user")

class ModelConnection(Base):
    """
    模型连接信息
    一个用户可能会配置多个模型
    """
    __tablename__ = "model_connections"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, index=True) # 用户自定义的模型名称

    model = Column(String) # 模型名称
    base_url = Column(String) # 模型 API 地址
    api_key = Column(String) # 模型 API 密钥

    model_description = Column(String, default="") # 模型描述
    model_avatar_url = Column(String, default="")  # 模型头像 URL
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 外键关联用户
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="model_connections")


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