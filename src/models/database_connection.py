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
    database_name = Column(String(100), unique=True, index=True) # 用户自定义的数据库名称

    database_uri = Column(String(500)) # 数据库 URI
    
    database_type = Column(String(50))              # 数据库类型
    database_description = Column(String(500), default="") # 数据库描述
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 外键关联用户
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="database_connections", foreign_keys=[user_id])

    def database(self) -> str:
        return self.database_uri.split("/")[-1]
