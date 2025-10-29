from pydantic import BaseModel, Field
from typing import Optional,List

class ModelConnectionCreate(BaseModel):
    """创建模型连接请求"""
    model_name: str = Field(..., description="用户自定义的模型名称")
    model: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="模型API地址")
    api_key: str = Field(..., description="模型API密钥")
    model_description: str = Field(default="", description="模型描述")
    model_avatar_url: str = Field(default="", description="模型头像URL")
    enable_thinking: bool = Field(default=False, description="是否启用思考")

class ModelConnectionUpdate(BaseModel):
    """更新模型连接请求"""
    model_name: Optional[str]  = Field(default=None, description="用户自定义的模型名称")
    model: Optional[str] = Field(default=None, description="模型名称")
    base_url: Optional[str] = Field(default=None, description="模型API地址")
    api_key: Optional[str] = Field(default=None, description="模型API密钥")
    model_description: Optional[str] = Field(default=None, description="模型描述")
    model_avatar_url: Optional[str] = Field(default=None, description="模型头像URL")
    enable_thinking: Optional[bool] = Field(default=None, description="是否启用思考")

class ModelConnectionResponse(BaseModel):
    """模型连接响应"""
    id: int = Field(..., description="模型连接ID")
    model_name: str = Field(..., description="用户自定义的模型名称")
    model: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="模型API地址")
    api_key: str = Field(..., description="混淆后的模型API密钥")
    model_description: str = Field(..., description="模型描述")
    model_avatar_url: str = Field(..., description="模型头像URL")
    enable_thinking: bool = Field(..., description="是否启用思考")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class ModelConnectionListResponse(BaseModel):
    """模型连接列表响应"""
    models: List[ModelConnectionResponse] = Field(..., description="模型连接列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")
    has_more: bool = Field(..., description="是否还有更多数据")
    active_connection_id: int = Field(0, description="当前用户活跃的模型连接ID，0表示无活跃连接")

class ActiveModelConnectionResponse(BaseModel):
    """活跃模型连接响应"""
    id: int = Field(..., description="模型连接ID")
    model_name: str = Field(..., description="用户自定义的模型名称")
    model: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="模型API地址")
    api_key: str = Field(..., description="混淆后的模型API密钥")
    model_description: str = Field(..., description="模型描述")
    model_avatar_url: str = Field(..., description="模型头像URL")
    enable_thinking: bool = Field(..., description="是否启用思考")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class SetActiveModelConnectionRequest(BaseModel):
    """设置活跃模型连接请求"""
    connection_id: int = Field(..., description="模型连接ID")

class SetActiveModelConnectionResponse(BaseModel):
    """设置活跃模型连接响应"""
    message: str = Field(..., description="设置结果消息")