from pydantic import BaseModel, Field
from typing import Optional,List

class DbSchemaCreate(BaseModel):
    """创建数据库模式请求"""
    schema_name: Optional[str] = Field(default=None, description="模式名称，不提供则自动生成UUID")
    schema_content: str = Field(..., description="模式内容（JSON字符串）")

class DbSchemaUpdate(BaseModel):
    """更新数据库模式请求"""
    schema_name: Optional[str] = Field(default=None, description="模式名称")
    schema_content: Optional[str] = Field(default=None, description="模式内容（JSON字符串）")

class DbSchemaResponse(BaseModel):
    """数据库模式响应"""
    id: int = Field(..., description="模式ID")
    schema_name: str = Field(..., description="模式名称")
    schema_content: str = Field(..., description="模式内容")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    user_id: int = Field(..., description="用户ID")

    class Config:
        from_attributes = True

class DbSchemaListResponse(BaseModel):
    """数据库模式列表响应"""
    schemas: List[DbSchemaResponse] = Field(..., description="模式列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")
    has_more: bool = Field(..., description="是否还有更多数据")
    active_schema_id: int = Field(0, description="当前用户活跃的数据库模式ID，0表示无活跃模式")

class DbSchemaDeleteResponse(BaseModel):
    """数据库模式删除响应"""
    message: str = Field(..., description="删除结果消息")

class ActiveDbSchemaResponse(BaseModel):
    """活跃数据库模式响应"""
    id: int = Field(..., description="模式ID")
    schema_name: str = Field(..., description="模式名称")
    schema_content: str = Field(..., description="模式内容")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    user_id: int = Field(..., description="用户ID")

    class Config:
        from_attributes = True

class SetActiveDbSchemaRequest(BaseModel):
    """设置活跃数据库模式请求"""
    schema_id: int = Field(..., description="模式ID")

class SetActiveDbSchemaResponse(BaseModel):
    """设置活跃数据库模式响应"""
    message: str = Field(..., description="设置结果消息")