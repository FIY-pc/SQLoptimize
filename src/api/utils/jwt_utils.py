from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Payload 模型
class JWTPayload(BaseModel):
    """JWT载荷基础模型"""
    sub: str  # 用户ID
    email: str  # 用户邮箱
    exp: datetime  # 过期时间
    type: str  # 令牌类型 (access/refresh)
    iat: Optional[datetime] = None  # 签发时间

class AccessTokenPayload(JWTPayload):
    """访问令牌载荷"""
    type: str = "access"

class RefreshTokenPayload(JWTPayload):
    """刷新令牌载荷"""
    type: str = "refresh"

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.secret_key = self.settings.jwt_secret_key
        self.algorithm = self.settings.jwt_algorithm
        self.access_token_expire_minutes = self.settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = self.settings.jwt_refresh_token_expire_days
    
    def create_access_token(self, user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        now = datetime.utcnow()
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = AccessTokenPayload(
            sub=user_id,
            email=email,
            exp=expire,
            iat=now
        )
        
        # 转换为字典进行编码
        to_encode = payload.model_dump()
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"创建访问令牌成功，用户ID: {user_id}")
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """创建刷新令牌"""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = RefreshTokenPayload(
            sub=user_id,
            email=email,
            exp=expire,
            iat=now
        )
        
        # 转换为字典进行编码
        to_encode = payload.model_dump()
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"创建刷新令牌成功，用户ID: {user_id}")
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[JWTPayload]:
        """验证令牌"""
        try:
            payload_dict = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload_dict.get("type") != token_type:
                logger.warning(f"令牌类型不匹配，期望: {token_type}, 实际: {payload_dict.get('type')}")
                return None
            
            # 检查过期时间
            exp = payload_dict.get("exp")
            if exp is None:
                logger.warning("令牌缺少过期时间")
                return None
            
            if datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning("令牌已过期")
                return None
            
            # 创建类型化的payload对象
            if token_type == "access":
                payload = AccessTokenPayload(**payload_dict)
            elif token_type == "refresh":
                payload = RefreshTokenPayload(**payload_dict)
            else:
                payload = JWTPayload(**payload_dict)
            
            logger.info(f"令牌验证成功，用户ID: {payload.sub}")
            return payload
            
        except JWTError as e:
            logger.error(f"令牌验证失败: {e}")
            return None
        except Exception as e:
            logger.error(f"令牌解析失败: {e}")
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[int]:
        """从令牌中获取用户ID"""
        payload = self.verify_token(token)
        if payload:
            try:
                return int(payload.sub)
            except (ValueError, TypeError):
                logger.error(f"无效的用户ID格式: {payload.sub}")
        return None

class PasswordManager:
    """密码管理器"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        hashed = pwd_context.hash(password)
        logger.info("密码哈希成功")
        return hashed
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        is_valid = pwd_context.verify(plain_password, hashed_password)
        if is_valid:
            logger.info("密码验证成功")
        else:
            logger.warning("密码验证失败")
        return is_valid

# 创建全局实例
jwt_manager = JWTManager()
password_manager = PasswordManager()
