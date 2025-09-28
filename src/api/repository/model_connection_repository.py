from sqlalchemy import and_
from typing import Optional, List
from src.models.model_connection import ModelConnection
from src.api.service_db import get_service_db
import logging

logger = logging.getLogger(__name__)

class ModelConnectionRepository:
    """模型连接数据访问层"""
    
    def __init__(self):
        pass
    
    def create(self, model_connection_data: dict) -> ModelConnection:
        """创建模型连接"""
        try:
            with get_service_db() as db:
                model_connection = ModelConnection(**model_connection_data)
                db.add(model_connection)
                db.commit()  # 提交事务
                db.refresh(model_connection)
                logger.info(f"模型连接创建成功: {model_connection.model_name}")
                return model_connection
        except Exception as e:
            logger.error(f"创建模型连接失败: {e}")
            raise
    
    def get_by_id(self, connection_id: int) -> Optional[ModelConnection]:
        """根据ID获取模型连接"""
        try:
            with get_service_db() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                return connection
        except Exception as e:
            logger.error(f"根据ID获取模型连接失败: {e}")
            raise
    
    def get_by_name(self, model_name: str) -> Optional[ModelConnection]:
        """根据模型名称获取模型连接"""
        try:
            with get_service_db() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first()
                return connection
        except Exception as e:
            logger.error(f"根据模型名称获取模型连接失败: {e}")
            raise
    
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ModelConnection]:
        """根据用户ID获取模型连接列表（分页）"""
        try:
            with get_service_db() as db:
                connections = db.query(ModelConnection).filter(
                    ModelConnection.user_id == user_id
                ).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"根据用户ID获取模型连接列表失败: {e}")
            raise
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelConnection]:
        """获取所有模型连接（分页）"""
        try:
            with get_service_db() as db:
                connections = db.query(ModelConnection).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"获取所有模型连接失败: {e}")
            raise
    
    def update(self, connection_id: int, connection_data: dict) -> Optional[ModelConnection]:
        """更新模型连接信息"""
        try:
            with get_service_db() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                if not connection:
                    return None
                
                for key, value in connection_data.items():
                    if hasattr(connection, key):
                        setattr(connection, key, value)
                
                db.commit()  # 提交事务
                db.refresh(connection)
                logger.info(f"模型连接更新成功: {connection.model_name}")
                return connection
        except Exception as e:
            logger.error(f"更新模型连接失败: {e}")
            raise
        
    def delete(self, connection_id: int) -> bool:
        """删除模型连接"""
        try:
            with get_service_db() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                if not connection:
                    return False
                
                # 先清除所有用户对该连接的活跃引用
                from src.models.user import User
                users_with_active_connection = db.query(User).filter(User.active_model_connections == connection_id).all()
                for user in users_with_active_connection:
                    user.active_model_connections = None
                    logger.info(f"清除用户 {user.id} 的活跃模型连接引用")
                
                db.delete(connection)
                db.commit()  # 提交事务
                logger.info(f"模型连接删除成功: {connection.model_name}")
                return True
        except Exception as e:
            logger.error(f"删除模型连接失败: {e}")
            raise
    
    def delete_by_name(self, model_name: str) -> bool:
        """根据模型名称删除模型连接"""
        try:
            with get_service_db() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first()
                if not connection:
                    return False
                
                # 先清除所有用户对该连接的活跃引用
                from src.models.user import User
                users_with_active_connection = db.query(User).filter(User.active_model_connections == connection.id).all()
                for user in users_with_active_connection:
                    user.active_model_connections = None
                    logger.info(f"清除用户 {user.id} 的活跃模型连接引用")
                
                db.delete(connection)
                db.commit()  # 提交事务
                logger.info(f"模型连接删除成功: {connection.model_name}")
                return True
        except Exception as e:
            logger.error(f"根据模型名称删除模型连接失败: {e}")
            raise
    
    def exists_by_name(self, model_name: str) -> bool:
        """检查模型名称是否已存在"""
        try:
            with get_service_db() as db:
                return db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first() is not None
        except Exception as e:
            logger.error(f"检查模型名称是否存在失败: {e}")
            raise
    
    def get_by_model(self, model: str) -> List[ModelConnection]:
        """根据模型名称获取模型连接列表"""
        try:
            with get_service_db() as db:
                connections = db.query(ModelConnection).filter(ModelConnection.model == model).all()
                return connections
        except Exception as e:
            logger.error(f"根据模型类型获取模型连接列表失败: {e}")
            raise
    
    def get_by_user_and_model(self, user_id: int, model: str) -> List[ModelConnection]:
        """根据用户ID和模型类型获取模型连接列表"""
        try:
            with get_service_db() as db:
                connections = db.query(ModelConnection).filter(
                    and_(ModelConnection.user_id == user_id, ModelConnection.model == model)
                ).all()
                return connections
        except Exception as e:
            logger.error(f"根据用户ID和模型类型获取模型连接列表失败: {e}")
            raise
    
    def count_by_user_id(self, user_id: int) -> int:
        """根据用户ID统计模型连接数量"""
        try:
            with get_service_db() as db:
                count = db.query(ModelConnection).filter(ModelConnection.user_id == user_id).count()
                return count
        except Exception as e:
            logger.error(f"统计用户模型连接数量失败: {e}")
            raise
    
    def get_active_by_user_id(self, user_id: int, auto_set_first: bool = True) -> Optional[ModelConnection]:
        """根据用户ID获取活跃的模型连接
        
        Args:
            user_id: 用户ID
            auto_set_first: 如果没有活跃连接，是否自动设置第一个连接为活跃
        """
        try:
            with get_service_db() as db:
                # 通过 User 模型的 active_model_connections 字段获取
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.active_model_connections:
                    if not auto_set_first:
                        return None
                    
                    # 自动设置第一个连接为活跃连接
                    user_connections = self.get_by_user_id(user_id, 0, 1)
                    if not user_connections:
                        return None
                    
                    first_connection = user_connections[0]
                    success = self.set_active_by_user_id(user_id, first_connection.id)
                    if success:
                        logger.info(f"自动设置用户 {user_id} 的第一个模型连接 {first_connection.id} 为活跃连接")
                        return first_connection
                    else:
                        logger.error(f"自动设置用户 {user_id} 的活跃模型连接失败")
                        return None
                
                connection = db.query(ModelConnection).filter(
                    ModelConnection.id == user.active_model_connections
                ).first()
                return connection
        except Exception as e:
            logger.error(f"根据用户ID获取活跃模型连接失败: {e}")
            raise
    
    def set_active_by_user_id(self, user_id: int, connection_id: int) -> bool:
        """设置用户的活跃模型连接"""
        try:
            with get_service_db() as db:
                # 检查连接是否存在且属于该用户
                connection = db.query(ModelConnection).filter(
                    ModelConnection.id == connection_id,
                    ModelConnection.user_id == user_id
                ).first()
                if not connection:
                    return False
                
                # 更新用户的 active_model_connections 字段
                from src.models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return False
                
                user.active_model_connections = connection_id
                db.commit()
                logger.info(f"设置用户 {user_id} 的活跃模型连接为 {connection_id}")
                return True
        except Exception as e:
            logger.error(f"设置用户活跃模型连接失败: {e}")
            raise