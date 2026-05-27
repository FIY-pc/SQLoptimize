from typing import Optional, List, cast
from sqlalchemy import select, func
from src.models.db_schema import DbSchema
from src.models.user import User
from src.api.service_db import get_async_db
import logging
from src.schemas.repository.db_schema import CreateDbSchemaReq

logger = logging.getLogger(__name__)

class DbSchemaRepository:
    """数据库模式数据访问层"""

    def __init__(self):
        pass

    async def create(self, schema_data: CreateDbSchemaReq) -> DbSchema:
        """创建数据库模式"""
        try:
            async with get_async_db() as db:
                schema = DbSchema(**schema_data.model_dump())
                db.add(schema)
                await db.commit()
                await db.refresh(schema)
                logger.info(f"数据库模式创建成功: {schema.schema_name}")
                return schema
        except Exception as e:
            logger.error(f"创建数据库模式失败: {e}")
            raise

    async def get_by_id(self, schema_id: int) -> Optional[DbSchema]:
        """根据ID获取数据库模式"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.id == schema_id)
                )
                return cast(Optional[DbSchema], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据ID获取数据库模式失败: {e}")
            raise

    async def get_by_name(self, schema_name: str) -> Optional[DbSchema]:
        """根据模式名称获取数据库模式"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.schema_name == schema_name)
                )
                return cast(Optional[DbSchema], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据模式名称获取数据库模式失败: {e}")
            raise

    async def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DbSchema]:
        """根据用户ID获取数据库模式列表（分页）"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema)
                    .where(DbSchema.user_id == user_id)
                    .offset(skip)
                    .limit(limit)
                )
                return cast(List[DbSchema], list(result.scalars().all()))
        except Exception as e:
            logger.error(f"根据用户ID获取数据库模式列表失败: {e}")
            raise

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[DbSchema]:
        """获取所有数据库模式（分页）"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).offset(skip).limit(limit)
                )
                return cast(List[DbSchema], list(result.scalars().all()))
        except Exception as e:
            logger.error(f"获取所有数据库模式失败: {e}")
            raise

    async def update(self, schema_id: int, schema_data: dict) -> Optional[DbSchema]:
        """更新数据库模式信息"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.id == schema_id)
                )
                schema: Optional[DbSchema] = result.scalar_one_or_none()
                if not schema:
                    return None

                for key, value in schema_data.items():
                    if hasattr(schema, key):
                        setattr(schema, key, value)

                await db.commit()
                await db.refresh(schema)
                logger.info(f"数据库模式更新成功: {schema.schema_name}")
                return schema
        except Exception as e:
            logger.error(f"更新数据库模式失败: {e}")
            raise

    async def delete(self, schema_id: int) -> bool:
        """删除数据库模式"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.id == schema_id)
                )
                schema: Optional[DbSchema] = result.scalar_one_or_none()
                if not schema:
                    return False

                # 先清除所有用户对该模式的活跃引用
                users_result = await db.execute(
                    select(User).where(User.active_db_schemas == schema_id)
                )
                users_with_active_schema = users_result.scalars().all()
                for user in users_with_active_schema:
                    user.active_db_schemas = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库模式引用")

                await db.delete(schema)
                await db.commit()
                logger.info(f"数据库模式删除成功: {schema.schema_name}")
                return True
        except Exception as e:
            logger.error(f"删除数据库模式失败: {e}")
            raise

    async def delete_by_name(self, schema_name: str) -> bool:
        """根据模式名称删除数据库模式"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.schema_name == schema_name)
                )
                schema: Optional[DbSchema] = result.scalar_one_or_none()
                if not schema:
                    return False

                # 先清除所有用户对该模式的活跃引用
                users_result = await db.execute(
                    select(User).where(User.active_db_schemas == schema.id)
                )
                users_with_active_schema = users_result.scalars().all()
                for user in users_with_active_schema:
                    user.active_db_schemas = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库模式引用")

                await db.delete(schema)
                await db.commit()
                logger.info(f"数据库模式删除成功: {schema.schema_name}")
                return True
        except Exception as e:
            logger.error(f"根据模式名称删除数据库模式失败: {e}")
            raise

    async def exists_by_name(self, schema_name: str) -> bool:
        """检查模式名称是否已存在"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(DbSchema.schema_name == schema_name)
                )
                return cast(Optional[DbSchema], result.scalar_one_or_none()) is not None
        except Exception as e:
            logger.error(f"检查模式名称是否存在失败: {e}")
            raise

    async def get_by_user_and_name(self, user_id: int, schema_name: str) -> Optional[DbSchema]:
        """根据用户ID和模式名称获取数据库模式"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(DbSchema).where(
                        DbSchema.user_id == user_id,
                        DbSchema.schema_name == schema_name
                    )
                )
                return cast(Optional[DbSchema], result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据用户ID和模式名称获取数据库模式失败: {e}")
            raise

    async def count_by_user_id(self, user_id: int) -> int:
        """根据用户ID统计数据库模式数量"""
        try:
            async with get_async_db() as db:
                result = await db.execute(
                    select(func.count()).select_from(DbSchema).where(DbSchema.user_id == user_id)
                )
                return cast(int, result.scalar() or 0)
        except Exception as e:
            logger.error(f"统计用户数据库模式数量失败: {e}")
            raise

    async def get_active_by_user_id(self, user_id: int, auto_set_first: bool = True) -> Optional[DbSchema]:
        """根据用户ID获取活跃的数据库模式

        Args:
            user_id: 用户ID
            auto_set_first: 如果没有活跃模式，是否自动设置第一个模式为活跃
        """
        try:
            async with get_async_db() as db:
                # 通过 User 模型的 active_db_schemas 字段获取
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user: Optional[User] = user_result.scalar_one_or_none()
                if not user or not user.active_db_schemas:
                    if not auto_set_first:
                        return None

                    # 自动设置第一个模式为活跃模式
                    user_schemas = await self.get_by_user_id(user_id, 0, 1)
                    if not user_schemas:
                        return None

                    first_schema = user_schemas[0]
                    success = await self.set_active_by_user_id(user_id, first_schema.id)
                    if success:
                        logger.info(f"自动设置用户 {user_id} 的第一个数据库模式 {first_schema.id} 为活跃模式")
                        return first_schema
                    else:
                        logger.error(f"自动设置用户 {user_id} 的活跃数据库模式失败")
                        return None

                schema_result = await db.execute(
                    select(DbSchema).where(DbSchema.id == user.active_db_schemas)
                )
                return cast(Optional[DbSchema], schema_result.scalar_one_or_none())
        except Exception as e:
            logger.error(f"根据用户ID获取活跃数据库模式失败: {e}")
            raise

    async def set_active_by_user_id(self, user_id: int, schema_id: int) -> bool:
        """设置用户的活跃数据库模式"""
        try:
            async with get_async_db() as db:
                # 检查模式是否存在且属于该用户
                schema_result = await db.execute(
                    select(DbSchema).where(
                        DbSchema.id == schema_id,
                        DbSchema.user_id == user_id
                    )
                )
                schema: Optional[DbSchema] = schema_result.scalar_one_or_none()
                if not schema:
                    return False

                # 更新用户的 active_db_schemas 字段
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user: Optional[User] = user_result.scalar_one_or_none()
                if not user:
                    return False

                user.active_db_schemas = schema_id
                await db.commit()
                logger.info(f"设置用户 {user_id} 的活跃数据库模式为 {schema_id}")
                return True
        except Exception as e:
            logger.error(f"设置用户活跃数据库模式失败: {e}")
            raise