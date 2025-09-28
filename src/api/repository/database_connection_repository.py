from sqlalchemy import and_
from typing import Optional, List
from src.models.database_connection import DatabaseConnection
from src.api.service_db import get_service_db
import logging

logger = logging.getLogger(__name__)

class DatabaseConnectionRepository:
    """数据库连接数据访问层"""
    
    def __init__(self):
        pass
    
    def create(self, database_connection_data: dict) -> DatabaseConnection:
        """创建数据库连接"""
        try:
            with get_service_db() as db:
                database_connection = DatabaseConnection(**database_connection_data)
                db.add(database_connection)
                db.commit()  # 提交事务
                db.refresh(database_connection)
                logger.info(f"数据库连接创建成功: {database_connection.database_name}")
                return database_connection
        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            raise 
    
    def get_by_id(self, connection_id: int) -> Optional[DatabaseConnection]:
        """根据ID获取数据库连接"""
        try: 
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                return connection
        except Exception as e:
            logger.error(f"根据ID获取数据库连接失败: {e}")
            raise
    
    def get_by_name(self, database_name: str) -> Optional[DatabaseConnection]:
        """根据数据库名称获取数据库连接"""
        try:
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first()
                return connection
        except Exception as e:
            logger.error(f"根据数据库名称获取数据库连接失败: {e}")
            raise
    
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DatabaseConnection]:
        """根据用户ID获取数据库连接列表（分页）"""
        try:
            with get_service_db() as db:
                connections = db.query(DatabaseConnection).filter(
                    DatabaseConnection.user_id == user_id
                ).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"根据用户ID获取数据库连接列表失败: {e}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[DatabaseConnection]:
        """获取所有数据库连接（分页）"""
        try:
            with get_service_db() as db:
                connections = db.query(DatabaseConnection).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"获取所有数据库连接失败: {e}")
            raise
    
    def update(self, connection_id: int, connection_data: dict) -> Optional[DatabaseConnection]:
        """更新数据库连接信息"""
        try:
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                if not connection:
                    return None
                
                for key, value in connection_data.items():
                    if hasattr(connection, key):
                        setattr(connection, key, value)
                
                db.commit()  # 提交事务
                db.refresh(connection)
                logger.info(f"数据库连接更新成功: {connection.database_name}")
                return connection
        except Exception as e:
            logger.error(f"更新数据库连接失败: {e}")
            raise
    
    def delete(self, connection_id: int) -> bool:
        """删除数据库连接"""
        try:
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                if not connection:
                    return False
                
                # 先清除所有用户对该连接的活跃引用
                from src.models.user import User
                users_with_active_connection = db.query(User).filter(User.active_database_connections == connection_id).all()
                for user in users_with_active_connection:
                    user.active_database_connections = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库连接引用")
                
                db.delete(connection)
                db.commit()  # 提交事务
                logger.info(f"数据库连接删除成功: {connection.database_name}")
                return True
        except Exception as e:
            logger.error(f"删除数据库连接失败: {e}")
            raise
    
    def delete_by_name(self, database_name: str) -> bool:
        """根据数据库名称删除数据库连接"""
        try:
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first()
                if not connection:
                    return False
                
                # 先清除所有用户对该连接的活跃引用
                from src.models.user import User
                users_with_active_connection = db.query(User).filter(User.active_database_connections == connection.id).all()
                for user in users_with_active_connection:
                    user.active_database_connections = None
                    logger.info(f"清除用户 {user.id} 的活跃数据库连接引用")
                
                db.delete(connection)
                db.commit()  # 提交事务
                logger.info(f"数据库连接删除成功: {connection.database_name}")
                return True
        except Exception as e:
            logger.error(f"根据数据库名称删除数据库连接失败: {e}")
            raise
    
    def exists_by_name(self, database_name: str) -> bool:
        """检查数据库名称是否已存在"""
        try:
            with get_service_db() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first()
                return connection is not None
        except Exception as e:
            logger.error(f"检查数据库名称是否存在失败: {e}")
            raise
    
    def get_by_database_type(self, database_type: str) -> List[DatabaseConnection]:
        """根据数据库类型获取数据库连接列表"""
        try:
            with get_service_db() as db:
                connections = db.query(DatabaseConnection).filter(DatabaseConnection.database_type == database_type).all()
                return connections
        except Exception as e:
            logger.error(f"根据数据库类型获取数据库连接列表失败: {e}")
            raise
    
    def get_by_user_and_type(self, user_id: int, database_type: str) -> List[DatabaseConnection]:
        """根据用户ID和数据库类型获取数据库连接列表"""
        try:
            with get_service_db() as db:
                connections = db.query(DatabaseConnection).filter(
                    and_(DatabaseConnection.user_id == user_id, DatabaseConnection.database_type == database_type)
                ).all()
                return connections
        except Exception as e:
            logger.error(f"根据用户ID和数据库类型获取数据库连接列表失败: {e}")
            raise
    
    def get_active_by_user_id(self, user_id: int, auto_set_first: bool = True) -> Optional[DatabaseConnection]:
        """根据用户ID获取活跃的数据库连接
        
        Args:
            user_id: 用户ID
            auto_set_first: 如果没有活跃连接，是否自动设置第一个连接为活跃
        """
        try:
            with get_service_db() as db:
                # 通过 User 模型的 active_database_connections 字段获取
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.active_database_connections:
                    if not auto_set_first:
                        return None
                    
                    # 自动设置第一个连接为活跃连接
                    user_connections = self.get_by_user_id(user_id, 0, 1)
                    if not user_connections:
                        return None
                    
                    first_connection = user_connections[0]
                    success = self.set_active_by_user_id(user_id, first_connection.id)
                    if success:
                        logger.info(f"自动设置用户 {user_id} 的第一个数据库连接 {first_connection.id} 为活跃连接")
                        return first_connection
                    else:
                        logger.error(f"自动设置用户 {user_id} 的活跃数据库连接失败")
                        return None
                
                connection = db.query(DatabaseConnection).filter(
                    DatabaseConnection.id == user.active_database_connections
                ).first()
                return connection
        except Exception as e:
            logger.error(f"根据用户ID获取活跃数据库连接失败: {e}")
            raise
    
    def set_active_by_user_id(self, user_id: int, connection_id: int) -> bool:
        """设置用户的活跃数据库连接"""
        try:
            with get_service_db() as db:
                # 检查连接是否存在且属于该用户
                connection = db.query(DatabaseConnection).filter(
                    DatabaseConnection.id == connection_id,
                    DatabaseConnection.user_id == user_id
                ).first()
                if not connection:
                    return False
                
                # 更新用户的 active_database_connections 字段
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.active_database_connections = connection_id
                db.commit()
                logger.info(f"设置用户 {user_id} 的活跃数据库连接为 {connection_id}")
                return True
        except Exception as e:
            logger.error(f"设置用户活跃数据库连接失败: {e}")
            raise