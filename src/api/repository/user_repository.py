from typing import Optional, List
from src.models.user import User
from src.api.service_db import get_service_db
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    """用户数据访问层"""
    
    def __init__(self):
        pass
    
    def create(self, user_data: dict) -> User:
        """创建用户"""
        try:
            with get_service_db() as db:
                # 如果传入了db会话，直接使用
                user = User(**user_data)
                db.add(user)
                db.commit()  # 提交事务
                db.refresh(user)
                logger.info(f"用户创建成功: {user.email}")
                return user
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            raise
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            with get_service_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                return user
        except Exception as e:
            logger.error(f"根据ID获取用户失败: {e}")
            raise
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            with get_service_db() as db:
                user = db.query(User).filter(User.email == email).first()
                return user
        except Exception as e:
            logger.error(f"根据邮箱获取用户失败: {e}")
            raise
    
    def get_by_name(self, name: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            with get_service_db() as db:
                user = db.query(User).filter(User.name == name).first()
                return user
        except Exception as e:
            logger.error(f"根据用户名获取用户失败: {e}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取所有用户（分页）"""
        try:
            with get_service_db() as db:
                users = db.query(User).offset(skip).limit(limit).all()
                return users
        except Exception as e:
            logger.error(f"获取所有用户失败: {e}")
            raise
    
    def update(self, user_id: int, user_data: dict) -> Optional[User]:
        """更新用户信息"""
        try:
            with get_service_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return None
                
                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                
                db.commit()  # 提交事务
                db.refresh(user)
                logger.info(f"用户更新成功: {user.email}")
                return user
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            raise
    
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        try:
            with get_service_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                db.delete(user)
                db.commit()  # 提交事务
                logger.info(f"用户删除成功: {user.email}")
                return True
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            raise
    
    def exists_by_email(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        try:
            with get_service_db() as db:
                return db.query(User).filter(User.email == email).first() is not None
        except Exception as e:
            logger.error(f"检查邮箱是否存在失败: {e}")
            raise
    
    def exists_by_name(self, name: str) -> bool:
        """检查用户名是否已存在"""
        try:
            with get_service_db() as db:
                return db.query(User).filter(User.name == name).first() is not None
        except Exception as e:
            logger.error(f"检查用户名是否存在失败: {e}")
            raise
