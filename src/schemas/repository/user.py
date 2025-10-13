from pydantic import BaseModel, EmailStr, Field

class CreateUserReq(BaseModel):
    name: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")