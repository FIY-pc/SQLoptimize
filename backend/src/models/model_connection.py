from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class ModelConnection(Base):
    """
    模型连接信息
    一个用户可能会配置多个模型
    """
    __tablename__ = "model_connections"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), unique=True, index=True) # 用户自定义的模型名称

    model = Column(String(100)) # 模型名称
    base_url = Column(String(500)) # 模型 API 地址
    api_key = Column(String(500)) # 模型 API 密钥

    model_description = Column(String(500), default="") # 模型描述
    model_avatar_url = Column(String(500), default="")  # 模型头像 URL

    enable_thinking = Column(Boolean, default=False) # 是否启用思考
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 外键关联用户
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="model_connections", foreign_keys=[user_id])