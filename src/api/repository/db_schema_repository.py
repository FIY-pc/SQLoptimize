from typing import Optional, List
from src.models.db_schema import DbSchema
from src.api.service_db import get_service_db
import logging

logger = logging.getLogger(__name__)

class DbSchemaRepository:
    """数据库模式数据访问层"""
    
    def __init__(self):
        pass
    
    def create(self, schema_data: dict) -> DbSchema:
        """创建数据库模式"""
        try:
            with get_service_db() as db:
                schema = DbSchema(**schema_data)
                db.add(schema)
                db.commit()  # 提交事务
                db.refresh(schema)
                logger.info(f"数据库模式创建成功: {schema.schema_name}")
                return schema
        except Exception as e:
            logger.error(f"创建数据库模式失败: {e}")
            raise 
    
    def get_by_id(self, schema_id: int) -> Optional[DbSchema]:
        """根据ID获取数据库模式"""
        try: 
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.id == schema_id).first()
                return schema
        except Exception as e:
            logger.error(f"根据ID获取数据库模式失败: {e}")
            raise
    
    def get_by_name(self, schema_name: str) -> Optional[DbSchema]:
        """根据模式名称获取数据库模式"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.schema_name == schema_name).first()
                return schema
        except Exception as e:
            logger.error(f"根据模式名称获取数据库模式失败: {e}")
            raise
    
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DbSchema]:
        """根据用户ID获取数据库模式列表（分页）"""
        try:
            with get_service_db() as db:
                schemas = db.query(DbSchema).filter(
                    DbSchema.user_id == user_id
                ).offset(skip).limit(limit).all()
                return schemas
        except Exception as e:
            logger.error(f"根据用户ID获取数据库模式列表失败: {e}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[DbSchema]:
        """获取所有数据库模式（分页）"""
        try:
            with get_service_db() as db:
                schemas = db.query(DbSchema).offset(skip).limit(limit).all()
                return schemas
        except Exception as e:
            logger.error(f"获取所有数据库模式失败: {e}")
            raise
    
    def update(self, schema_id: int, schema_data: dict) -> Optional[DbSchema]:
        """更新数据库模式信息"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.id == schema_id).first()
                if not schema:
                    return None
                
                for key, value in schema_data.items():
                    if hasattr(schema, key):
                        setattr(schema, key, value)
                
                db.commit()  # 提交事务
                db.refresh(schema)
                logger.info(f"数据库模式更新成功: {schema.schema_name}")
                return schema
        except Exception as e:
            logger.error(f"更新数据库模式失败: {e}")
            raise
    
    def delete(self, schema_id: int) -> bool:
        """删除数据库模式"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.id == schema_id).first()
                if not schema:
                    return False
                
                # 先清除所有用户对该模式的活跃引用
                from src.models.user import User
                users_with_active_schema = db.query(User).filter(User.active_db_schemas == schema_id).all()
                for user in users_with_active_schema:
                    user.active_db_schemas = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库模式引用")
                
                db.delete(schema)
                db.commit()  # 提交事务
                logger.info(f"数据库模式删除成功: {schema.schema_name}")
                return True
        except Exception as e:
            logger.error(f"删除数据库模式失败: {e}")
            raise
    
    def delete_by_name(self, schema_name: str) -> bool:
        """根据模式名称删除数据库模式"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.schema_name == schema_name).first()
                if not schema:
                    return False
                
                # 先清除所有用户对该模式的活跃引用
                from src.models.user import User
                users_with_active_schema = db.query(User).filter(User.active_db_schemas == schema.id).all()
                for user in users_with_active_schema:
                    user.active_db_schemas = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库模式引用")
                
                db.delete(schema)
                db.commit()  # 提交事务
                logger.info(f"数据库模式删除成功: {schema.schema_name}")
                return True
        except Exception as e:
            logger.error(f"根据模式名称删除数据库模式失败: {e}")
            raise
    
    def exists_by_name(self, schema_name: str) -> bool:
        """检查模式名称是否已存在"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(DbSchema.schema_name == schema_name).first()
                return schema is not None
        except Exception as e:
            logger.error(f"检查模式名称是否存在失败: {e}")
            raise
    
    def get_by_user_and_name(self, user_id: int, schema_name: str) -> Optional[DbSchema]:
        """根据用户ID和模式名称获取数据库模式"""
        try:
            with get_service_db() as db:
                schema = db.query(DbSchema).filter(
                    DbSchema.user_id == user_id,
                    DbSchema.schema_name == schema_name
                ).first()
                return schema
        except Exception as e:
            logger.error(f"根据用户ID和模式名称获取数据库模式失败: {e}")
            raise
    
    def get_active_by_user_id(self, user_id: int, auto_set_first: bool = True) -> Optional[DbSchema]:
        """根据用户ID获取活跃的数据库模式
        
        Args:
            user_id: 用户ID
            auto_set_first: 如果没有活跃模式，是否自动设置第一个模式为活跃
        """
        try:
            with get_service_db() as db:
                # 通过 User 模型的 active_db_schemas 字段获取
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.active_db_schemas:
                    if not auto_set_first:
                        return None
                    
                    # 自动设置第一个模式为活跃模式
                    user_schemas = self.get_by_user_id(user_id, 0, 1)
                    if not user_schemas:
                        return None
                    
                    first_schema = user_schemas[0]
                    success = self.set_active_by_user_id(user_id, first_schema.id)
                    if success:
                        logger.info(f"自动设置用户 {user_id} 的第一个数据库模式 {first_schema.id} 为活跃模式")
                        return first_schema
                    else:
                        logger.error(f"自动设置用户 {user_id} 的活跃数据库模式失败")
                        return None
                
                schema = db.query(DbSchema).filter(
                    DbSchema.id == user.active_db_schemas
                ).first()
                return schema
        except Exception as e:
            logger.error(f"根据用户ID获取活跃数据库模式失败: {e}")
            raise
    
    def set_active_by_user_id(self, user_id: int, schema_id: int) -> bool:
        """设置用户的活跃数据库模式"""
        try:
            with get_service_db() as db:
                # 检查模式是否存在且属于该用户
                schema = db.query(DbSchema).filter(
                    DbSchema.id == schema_id,
                    DbSchema.user_id == user_id
                ).first()
                if not schema:
                    return False
                
                # 更新用户的 active_db_schemas 字段
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.active_db_schemas = schema_id
                db.commit()
                logger.info(f"设置用户 {user_id} 的活跃数据库模式为 {schema_id}")
                return True
        except Exception as e:
            logger.error(f"设置用户活跃数据库模式失败: {e}")
            raise
