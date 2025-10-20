from pydantic import BaseModel, Field

class CreateModelConnectionReq(BaseModel):
    model_name: str = Field(..., description="模型名称")
    model: str = Field(..., description="模型名称")
    base_url: str = Field(..., description="模型API地址")
    api_key: str = Field(..., description="模型API密钥")
    model_description: str = Field(default="", description="模型描述")
    model_avatar_url: str = Field(default="", description="模型头像URL")
    user_id: int = Field(..., description="用户ID")