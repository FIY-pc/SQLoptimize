from pydantic import BaseModel, Field

class CreateDbSchemaReq(BaseModel):
    schema_name: str = Field(..., description="模式名称")
    schema_content: str = Field(..., description="模式内容")
    user_id: int = Field(..., description="用户ID")