from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from src.api.model import ModelConnection
from src.api.database import get_db_context
import logging

logger = logging.getLogger(__name__)

class ModelConnectionRepository:
    """模型连接数据访问层"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    def create(self, model_connection_data: dict) -> ModelConnection:
        """创建模型连接"""
        try:
            if self.db:
                # 如果传入了db会话，直接使用
                model_connection = ModelConnection(**model_connection_data)
                self.db.add(model_connection)
                self.db.flush()
                self.db.refresh(model_connection)
                logger.info(f"模型连接创建成功: {model_connection.model_name}")
                return model_connection
            else:
                # 如果没有传入db会话，使用上下文管理器
                with get_db_context() as db:
                    model_connection = ModelConnection(**model_connection_data)
                    db.add(model_connection)
                    db.flush()
                    db.refresh(model_connection)
                    logger.info(f"模型连接创建成功: {model_connection.model_name}")
                    return model_connection
        except Exception as e:
            logger.error(f"创建模型连接失败: {e}")
            raise
    
    def get_by_id(self, connection_id: int) -> Optional[ModelConnection]:
        """根据ID获取模型连接"""
        try:
            if self.db:
                connection = self.db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                return connection
            else:
                with get_db_context() as db:
                    connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                    return connection
        except Exception as e:
            logger.error(f"根据ID获取模型连接失败: {e}")
            raise
    
    def get_by_name(self, model_name: str) -> Optional[ModelConnection]:
        """根据模型名称获取模型连接"""
        try:
            with get_db_context() as db:
                connection = db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first()
                return connection
        except Exception as e:
            logger.error(f"根据模型名称获取模型连接失败: {e}")
            raise
    
    def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ModelConnection]:
        """根据用户ID获取模型连接列表（分页）"""
        try:
            if self.db:
                connections = self.db.query(ModelConnection).filter(
                    ModelConnection.user_id == user_id
                ).offset(skip).limit(limit).all()
                return connections
            else:
                with get_db_context() as db:
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
            with get_db_context() as db:
                connections = db.query(ModelConnection).offset(skip).limit(limit).all()
                return connections
        except Exception as e:
            logger.error(f"获取所有模型连接失败: {e}")
            raise
    
    def update(self, connection_id: int, connection_data: dict) -> Optional[ModelConnection]:
        """更新模型连接信息"""
        try:
            if self.db:
                connection = self.db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                if not connection:
                    return None
                
                for key, value in connection_data.items():
                    if hasattr(connection, key):
                        setattr(connection, key, value)
                
                self.db.flush()
                self.db.refresh(connection)
                logger.info(f"模型连接更新成功: {connection.model_name}")
                return connection
            else:
                with get_db_context() as db:
                    connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                    if not connection:
                        return None
                    
                    for key, value in connection_data.items():
                        if hasattr(connection, key):
                            setattr(connection, key, value)
                    
                    db.flush()
                    db.refresh(connection)
                    logger.info(f"模型连接更新成功: {connection.model_name}")
                    return connection
        except Exception as e:
            logger.error(f"更新模型连接失败: {e}")
            raise
        
    def delete(self, connection_id: int) -> bool:
        """删除模型连接"""
        try:
            if self.db:
                connection = self.db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                if not connection:
                    return False
                
                self.db.delete(connection)
                logger.info(f"模型连接删除成功: {connection.model_name}")
                return True
            else:
                with get_db_context() as db:
                    connection = db.query(ModelConnection).filter(ModelConnection.id == connection_id).first()
                    if not connection:
                        return False
                    
                    db.delete(connection)
                    logger.info(f"模型连接删除成功: {connection.model_name}")
                    return True
        except Exception as e:
            logger.error(f"删除模型连接失败: {e}")
            raise
    
    def delete_by_name(self, model_name: str) -> bool:
        """根据模型名称删除模型连接"""
        try:
            if self.db:
                connection = self.db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first()
                if not connection:
                    return False
                
                self.db.delete(connection)
                logger.info(f"模型连接删除成功: {connection.model_name}")
                return True
            else:
                with get_db_context() as db:
                    connection = db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first()
                    if not connection:
                        return False
                    
                    db.delete(connection)
                    logger.info(f"模型连接删除成功: {connection.model_name}")
                    return True
        except Exception as e:
            logger.error(f"根据模型名称删除模型连接失败: {e}")
            raise
    
    def exists_by_name(self, model_name: str) -> bool:
        """检查模型名称是否已存在"""
        try:
            if self.db:
                return self.db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first() is not None
            else:
                with get_db_context() as db:
                    return db.query(ModelConnection).filter(ModelConnection.model_name == model_name).first() is not None
        except Exception as e:
            logger.error(f"检查模型名称是否存在失败: {e}")
            raise
    
    def get_by_model(self, model: str) -> List[ModelConnection]:
        """根据模型名称获取模型连接列表"""
        try:
            if self.db:
                connections = self.db.query(ModelConnection).filter(ModelConnection.model == model).all()
                return connections
            else:
                with get_db_context() as db:
                    connections = db.query(ModelConnection).filter(ModelConnection.model == model).all()
                    return connections
        except Exception as e:
            logger.error(f"根据模型类型获取模型连接列表失败: {e}")
            raise
    
    def get_by_user_and_model(self, user_id: int, model: str) -> List[ModelConnection]:
        """根据用户ID和模型类型获取模型连接列表"""
        try:
            if self.db:
                connections = self.db.query(ModelConnection).filter(
                    and_(ModelConnection.user_id == user_id, ModelConnection.model == model)
                ).all()
                return connections
            else:
                with get_db_context() as db:
                    connections = db.query(ModelConnection).filter(
                        and_(ModelConnection.user_id == user_id, ModelConnection.model == model)
                    ).all()
                    return connections
        except Exception as e:
            logger.error(f"根据用户ID和模型类型获取模型连接列表失败: {e}")
            raise
