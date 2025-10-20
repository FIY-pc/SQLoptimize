from pydantic import BaseModel, Field

class CreateDatabaseConnectionReq(BaseModel):
    database_name: str = Field(..., description="数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(default="opentenbase", description="数据库类型")
    database_description: str = Field(default="", description="数据库描述")
    user_id: int = Field(..., description="用户ID")