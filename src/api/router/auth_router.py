from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from src.api.repository import UserRepository
from src.api.utils import jwt_manager, password_manager
from src.api.database import get_db_context
import logging

logger = logging.getLogger(__name__)

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# HTTP Bearer认证
security = HTTPBearer()

# 请求和响应模型
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
    token_type: str = "bearer"

class UserInfo(BaseModel):
    id: int = Field(..., description="用户ID")
    name: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    created_at: str = Field(..., description="创建时间")

# 依赖项：获取当前用户
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取当前认证用户"""
    token = credentials.credentials
    payload = jwt_manager.verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.sub
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户信息
    with get_db_context() as db:
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(int(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 提取用户数据，避免会话依赖
        user_id = user.id
        user_name = user.name
        user_email = user.email
    
    return {
        "id": user_id,
        "name": user_name,
        "email": user_email
    }

@auth_router.post("/register", response_model=LoginResponse,summary="用户注册")
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        with get_db_context() as db:
            user_repo = UserRepository(db)
            
            # 检查邮箱是否已存在
            if user_repo.exists_by_email(request.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册"
                )
            
            # 检查用户名是否已存在
            if user_repo.exists_by_name(request.name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被使用"
                )
            
            # 创建用户
            user_data = {
                "name": request.name,
                "email": request.email,
                "password": password_manager.hash_password(request.password)
            }
            
            user = user_repo.create(user_data)
            
            # 生成令牌
            access_token = jwt_manager.create_access_token(str(user.id), user.email)
            refresh_token = jwt_manager.create_refresh_token(str(user.id), user.email)
            
            user_email = user.email
            response = LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user.id,
                user_name=user.name
            )
        
        logger.info(f"用户注册成功: {user_email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )

@auth_router.post("/login", response_model=LoginResponse,summary="用户登录")
async def login(request: LoginRequest):
    """用户登录"""
    try:
        with get_db_context() as db:
            user_repo = UserRepository(db)
            
            # 验证用户凭据
            user = user_repo.get_by_email(request.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户不存在",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 验证密码
            if not password_manager.verify_password(request.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="密码错误",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 生成令牌
            access_token = jwt_manager.create_access_token(str(user.id), user.email)
            refresh_token = jwt_manager.create_refresh_token(str(user.id), user.email)
            
            # 提取用户数据
            user_email = user.email
            response = LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user.id,
                user_name=user.name
            )

        logger.info(f"用户登录成功: {user_email}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

@auth_router.post("/refresh", response_model=RefreshTokenResponse,summary="刷新访问令牌")
async def refresh_token(request: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        # 验证刷新令牌
        payload = jwt_manager.verify_token(request.refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.sub
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌中缺少用户信息",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证用户是否存在
        with get_db_context() as db:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(int(user_id))
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户不存在",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 生成新的访问令牌
            access_token = jwt_manager.create_access_token(str(user.id), user.email)
            
            # 提取用户数据
            user_email = user.email
            response = RefreshTokenResponse(access_token=access_token)
        
        logger.info(f"令牌刷新成功: {user_email}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新失败，请稍后重试"
        )

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")

@auth_router.post("/change-password",summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    try:
        with get_db_context() as db:
            user_repo = UserRepository(db)
            user = user_repo.get_by_id(current_user["id"])
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在"
                )
            
            # 验证旧密码
            if not password_manager.verify_password(request.old_password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="原密码错误"
                )
            
            # 更新密码
            hashed_new_password = password_manager.hash_password(request.new_password)
            user_repo.update(current_user["id"], {"password": hashed_new_password})
        
        logger.info(f"用户修改密码成功: {current_user['email']}")
        return {"message": "密码修改成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败，请稍后重试"
        )
    