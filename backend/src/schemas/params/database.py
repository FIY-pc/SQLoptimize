from pydantic import BaseModel, Field
from typing import Optional,List

class DatabaseConnectionCreate(BaseModel):
    """创建数据库连接请求"""
    database_name: str = Field(..., description="用户自定义的数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(default="opentenbase", description="数据库类型")
    database_description: str = Field(default="", description="数据库描述")

class DatabaseConnectionUpdate(BaseModel):
    """更新数据库连接请求"""
    database_name: Optional[str] = Field(default=None, description="用户自定义的数据库名称")
    database_uri: Optional[str] = Field(default=None, description="数据库连接URI")
    database_type: Optional[str] = Field(default=None, description="数据库类型")
    database_description: Optional[str] = Field(default=None, description="数据库描述")

class DatabaseConnectionResponse(BaseModel):
    """数据库连接响应"""
    id: int = Field(..., description="数据库连接ID")
    database_name: str = Field(..., description="用户自定义的数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(..., description="数据库类型")
    database_description: str = Field(..., description="数据库描述")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class DatabaseConnectionListResponse(BaseModel):
    """数据库连接列表响应"""
    databases: List[DatabaseConnectionResponse] = Field(..., description="数据库连接列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")
    has_more: bool = Field(..., description="是否还有更多数据")
    active_connection_id: int = Field(0, description="当前用户活跃的数据库连接ID，0表示无活跃连接")

class DatabaseConnectionTestResponse(BaseModel):
    """数据库连接测试响应"""
    message: str = Field(..., description="测试结果消息")
    status: str = Field(..., description="测试状态：success/failed")
    response_time: float = Field(..., description="响应时间")

class DatabaseConnectionDeleteResponse(BaseModel):
    """数据库连接删除响应"""
    message: str = Field(..., description="删除结果消息")

class ActiveDatabaseConnectionResponse(BaseModel):
    """活跃数据库连接响应"""
    id: int = Field(..., description="数据库连接ID")
    database_name: str = Field(..., description="用户自定义的数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(..., description="数据库类型")
    database_description: str = Field(..., description="数据库描述")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class SetActiveDatabaseConnectionRequest(BaseModel):
    """设置活跃数据库连接请求"""
    connection_id: int = Field(..., description="数据库连接ID")

class SetActiveDatabaseConnectionResponse(BaseModel):
    """设置活跃数据库连接响应"""
    message: str = Field(..., description="设置结果消息")