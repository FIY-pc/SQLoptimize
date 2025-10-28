from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")

class RegisterRequest(BaseModel):
    name: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")  
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user_id: int = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")

class RefreshTokenResponse(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
class UserInfo(BaseModel):
    id: int = Field(..., description="用户ID")
    name: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    created_at: str = Field(..., description="创建时间")