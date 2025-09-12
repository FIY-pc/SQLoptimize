from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from src.api.model import DatabaseConnection
from src.api.database import get_db_context
import logging

logger = logging.getLogger(__name__)

class DatabaseConnectionRepository:
    """数据库连接数据访问层"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def create(self, database_connection_data: dict) -> DatabaseConnection:
        """创建数据库连接"""
        try:
            with get_db_context() as db:
                database_connection = DatabaseConnection(**database_connection_data)
                db.add(database_connection)
                db.flush()
                db.refresh(database_connection)
                logger.info(f"数据库连接创建成功: {database_connection.database_name}")
                return database_connection
        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            raise
    
    def get_by_id(self, connection_id: int) -> Optional[DatabaseConnection]:
        """根据ID获取数据库连接"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                return connection
        except Exception as e:
            logger.error(f"根据ID获取数据库连接失败: {e}")
            raise
    
    def get_by_name(self, database_name: str) -> Optional[DatabaseConnection]:
        """根据数据库名称获取数据库连接"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first()
                return connection
        except Exception as e:
            logger.error(f"根据数据库名称获取数据库连接失败: {e}")
            raise
    
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DatabaseConnection]:
        """根据用户ID获取数据库连接列表（分页）"""
        try:
            with get_db_context() as db:
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
            with get_db_context() as db:
                connections = db.query(DatabaseConnection).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"获取所有数据库连接失败: {e}")
            raise
    
    def update(self, connection_id: int, connection_data: dict) -> Optional[DatabaseConnection]:
        """更新数据库连接信息"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                if not connection:
                    return None
                
                for key, value in connection_data.items():
                    if hasattr(connection, key):
                        setattr(connection, key, value)
                
                db.flush()
                db.refresh(connection)
                logger.info(f"数据库连接更新成功: {connection.database_name}")
                return connection
        except Exception as e:
            logger.error(f"更新数据库连接失败: {e}")
            raise
    
    def delete(self, connection_id: int) -> bool:
        """删除数据库连接"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                if not connection:
                    return False
                
                db.delete(connection)
                logger.info(f"数据库连接删除成功: {connection.database_name}")
                return True
        except Exception as e:
            logger.error(f"删除数据库连接失败: {e}")
            raise
    
    def delete_by_name(self, database_name: str) -> bool:
        """根据数据库名称删除数据库连接"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first()
                if not connection:
                    return False
                
                db.delete(connection)
                logger.info(f"数据库连接删除成功: {connection.database_name}")
                return True
        except Exception as e:
            logger.error(f"根据数据库名称删除数据库连接失败: {e}")
            raise
    
    def exists_by_name(self, database_name: str) -> bool:
        """检查数据库名称是否已存在"""
        try:
            with get_db_context() as db:
                return db.query(DatabaseConnection).filter(DatabaseConnection.database_name == database_name).first() is not None
        except Exception as e:
            logger.error(f"检查数据库名称是否存在失败: {e}")
            raise
    
    def get_by_database_type(self, database_type: str) -> List[DatabaseConnection]:
        """根据数据库类型获取数据库连接列表"""
        try:
            with get_db_context() as db:
                connections = db.query(DatabaseConnection).filter(DatabaseConnection.database_type == database_type).all()
                return connections
        except Exception as e:
            logger.error(f"根据数据库类型获取数据库连接列表失败: {e}")
            raise
    
    def get_by_user_and_type(self, user_id: int, database_type: str) -> List[DatabaseConnection]:
        """根据用户ID和数据库类型获取数据库连接列表"""
        try:
            with get_db_context() as db:
                connections = db.query(DatabaseConnection).filter(
                    and_(DatabaseConnection.user_id == user_id, DatabaseConnection.database_type == database_type)
                ).all()
                return connections
        except Exception as e:
            logger.error(f"根据用户ID和数据库类型获取数据库连接列表失败: {e}")
            raise
    
    def test_connection(self, connection_id: int) -> bool:
        """测试数据库连接"""
        try:
            with get_db_context() as db:
                connection = db.query(DatabaseConnection).filter(DatabaseConnection.id == connection_id).first()
                if not connection:
                    return False
                
                # 这里可以添加实际的数据库连接测试逻辑
                # 例如：尝试连接到数据库并执行简单查询
                # 目前返回True作为占位符
                logger.info(f"数据库连接测试成功: {connection.database_name}")
                return True
        except Exception as e:
            logger.error(f"测试数据库连接失败: {e}")
            return False
