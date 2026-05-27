from typing import Optional, List, cast
from sqlalchemy import select, func
from src.models.user import User
from src.api.service_db import get_async_db
import logging
from src.schemas.repository.user import CreateUserReq

logger = logging.getLogger(__name__)

class UserRepository:
    """用户数据访问层"""

    def __init__(self):
        pass

    async def create(self, user_data: CreateUserReq) -> User:
        """创建用户"""
        try:
            async with get_async_db() as db:
                user = User(**user_data.model_dump())
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"用户创建成功: {user.email}")
                return user
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            raise

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                return cast(Optional[User], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据ID获取用户失败: {e}")
            raise

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                return cast(Optional[User], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据邮箱获取用户失败: {e}")
            raise

    async def get_by_name(self, name: str) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.name == name)
                )
                return cast(Optional[User], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据用户名获取用户失败: {e}")
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """获取所有用户（分页）"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).offset(skip).limit(limit)
                )
                return cast(List[User], list(result.scalars().all()))
        except Exception as e:
            logger.error(f"获取所有用户失败: {e}")
            raise

    async def update(self, user_id: int, user_data: dict) -> Optional[User]:
        """更新用户信息"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user: Optional[User] = result.scalar_one_or_none()
                if not user:
                    return None

                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)

                await db.commit()
                await db.refresh(user)
                logger.info(f"用户更新成功: {user.email}")
                return user
        except Exception as e:
            logger.error(f"更新用户失败: {e}")
            raise

    async def delete(self, user_id: int) -> bool:
        """删除用户"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user: Optional[User] = result.scalar_one_or_none()
                if not user:
                    return False

                await db.delete(user)
                await db.commit()
                logger.info(f"用户删除成功: {user.email}")
                return True
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            raise

    async def exists_by_email(self, email: str) -> bool:
        """检查邮箱是否已存在"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                return cast(Optional[User], result.scalar_one_or_none()) is not None
        except Exception as e:
            logger.error(f"检查邮箱是否存在失败: {e}")
            raise

    async def exists_by_name(self, name: str) -> bool:
        """检查用户名是否已存在"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(User).where(User.name == name)
                )
                return cast(Optional[User], result.scalar_one_or_none()) is not None
        except Exception as e:
            logger.error(f"检查用户名是否存在失败: {e}")
            raise