from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional
from src.api.repository import DatabaseConnectionRepository
from src.api.database import get_db_context
from src.api.utils import get_current_user
import logging

logger = logging.getLogger(__name__)

database_router = APIRouter(
    prefix="/api/databases",
    tags=["databases"],
    responses={404: {"description": "Not found"}},
)

# 请求和响应模型
class DatabaseConnectionCreate(BaseModel):
    """创建数据库连接请求"""
    database_name: str = Field(..., description="用户自定义的数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(..., description="数据库类型")
    database_description: str = Field(default="", description="数据库描述")

class DatabaseConnectionUpdate(BaseModel):
    """更新数据库连接请求"""
    database_name: Optional[str] = Field(default=None, description="用户自定义的数据库名称")
    database_uri: Optional[str] = Field(default=None, description="数据库连接URI")
    database_type: Optional[str] = Field(default=None, description="数据库类型")
    database_description: Optional[str] = Field(default=None, description="数据库描述")

class DatabaseConnectionResponse(BaseModel):
    """数据库连接响应"""
    id: int = Field(..., description="数据库连接ID")
    database_name: str = Field(..., description="用户自定义的数据库名称")
    database_uri: str = Field(..., description="数据库连接URI")
    database_type: str = Field(..., description="数据库类型")
    database_description: str = Field(..., description="数据库描述")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True

class DatabaseConnectionListResponse(BaseModel):
    """数据库连接列表响应"""
    databases: List[DatabaseConnectionResponse] = Field(..., description="数据库连接列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")

class DatabaseConnectionTestResponse(BaseModel):
    """数据库连接测试响应"""
    message: str = Field(..., description="测试结果消息")
    status: str = Field(..., description="测试状态：success/failed")

class DatabaseConnectionDeleteResponse(BaseModel):
    """数据库连接删除响应"""
    message: str = Field(..., description="删除结果消息")

@database_router.get("/", response_model=DatabaseConnectionListResponse, summary="获取用户数据库连接列表")
async def get_user_databases(
    skip: int = 0,
    limit: int = 100,
    database_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的数据库连接列表"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            if database_type:
                connections = db_repo.get_by_user_and_type(current_user["id"], database_type)
            else:
                connections = db_repo.get_by_user_id(current_user["id"], skip, limit)
            
            # 转换为响应模型
            database_responses = []
            for conn in connections:
                database_responses.append(DatabaseConnectionResponse(
                    id=conn.id,
                    database_name=conn.database_name,
                    database_uri=conn.database_uri,
                    database_type=conn.database_type,
                    database_description=conn.database_description,
                    created_at=conn.created_at.isoformat() if conn.created_at else "",
                    updated_at=conn.updated_at.isoformat() if conn.updated_at else ""
                ))
            
            # 获取总数（用于分页）
            total_connections = db_repo.get_by_user_id(current_user["id"], 0, 1000)
            total = len(total_connections)
            
            logger.info(f"获取用户数据库连接列表成功，用户ID: {current_user['id']}, 数量: {len(database_responses)}")
            
            return DatabaseConnectionListResponse(
                databases=database_responses,
                total=total,
                skip=skip,
                limit=limit
            )
            
    except Exception as e:
        logger.error(f"获取用户数据库连接列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库连接列表失败，请稍后重试"
        )

@database_router.post("/", response_model=DatabaseConnectionResponse, summary="创建数据库连接")
async def create_database_connection(
    request: DatabaseConnectionCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新的数据库连接"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            
            # 检查数据库名称是否已存在
            if db_repo.exists_by_name(request.database_name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="数据库名称已存在"
                )
            
            # 创建数据库连接
            connection_data = {
                "database_name": request.database_name,
                "database_uri": request.database_uri,
                "database_type": request.database_type,
                "database_description": request.database_description,
                "user_id": current_user["id"]
            }
            
            connection = db_repo.create(connection_data)
            
            # 转换为响应模型
            response = DatabaseConnectionResponse(
                id=connection.id,
                database_name=connection.database_name,
                database_uri=connection.database_uri,
                database_type=connection.database_type,
                database_description=connection.database_description,
                created_at=connection.created_at.isoformat() if connection.created_at else "",
                updated_at=connection.updated_at.isoformat() if connection.updated_at else ""
            )
            
            logger.info(f"创建数据库连接成功，用户ID: {current_user['id']}, 数据库名称: {connection.database_name}")
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建数据库连接失败，请稍后重试"
        )

@database_router.get("/{connection_id}", response_model=DatabaseConnectionResponse, summary="根据ID获取数据库连接")
async def get_database_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取指定的数据库连接信息"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            connection = db_repo.get_by_id(connection_id)
            
            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="数据库连接不存在"
                )
            
            # 检查是否属于当前用户
            if connection.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问此数据库连接"
                )
            
            # 转换为响应模型
            response = DatabaseConnectionResponse(
                id=connection.id,
                database_name=connection.database_name,
                database_uri=connection.database_uri,
                database_type=connection.database_type,
                database_description=connection.database_description,
                created_at=connection.created_at.isoformat() if connection.created_at else "",
                updated_at=connection.updated_at.isoformat() if connection.updated_at else ""
            )
            
            logger.info(f"获取数据库连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据库连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库连接失败，请稍后重试"
        )

@database_router.put("/{connection_id}", response_model=DatabaseConnectionResponse, summary="更新数据库连接")
async def update_database_connection(
    connection_id: int,
    request: DatabaseConnectionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新数据库连接信息"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            
            # 检查数据库连接是否存在
            connection = db_repo.get_by_id(connection_id)
            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="数据库连接不存在"
                )
            
            # 检查是否属于当前用户
            if connection.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权修改此数据库连接"
                )
            
            # 如果更新数据库名称，检查是否与其他连接冲突
            if request.database_name and request.database_name != connection.database_name:
                if db_repo.exists_by_name(request.database_name):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="数据库名称已存在"
                    )
            
            # 准备更新数据（只包含非None的字段）
            update_data = {}
            for field, value in request.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            
            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有提供要更新的字段"
                )
            
            # 更新数据库连接
            updated_connection = db_repo.update(connection_id, update_data)
            
            # 转换为响应模型
            response = DatabaseConnectionResponse(
                id=updated_connection.id,
                database_name=updated_connection.database_name,
                database_uri=updated_connection.database_uri,
                database_type=updated_connection.database_type,
                database_description=updated_connection.database_description,
                created_at=updated_connection.created_at.isoformat() if updated_connection.created_at else "",
                updated_at=updated_connection.updated_at.isoformat() if updated_connection.updated_at else ""
            )
            
            logger.info(f"更新数据库连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据库连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新数据库连接失败，请稍后重试"
        )

@database_router.delete("/{connection_id}", response_model=DatabaseConnectionDeleteResponse, summary="删除数据库连接")
async def delete_database_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除数据库连接"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            
            # 检查数据库连接是否存在
            connection = db_repo.get_by_id(connection_id)
            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="数据库连接不存在"
                )
            
            # 检查是否属于当前用户
            if connection.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权删除此数据库连接"
                )
            
            # 删除数据库连接
            success = db_repo.delete(connection_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="删除数据库连接失败"
                )
            
            logger.info(f"删除数据库连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
            return DatabaseConnectionDeleteResponse(message="数据库连接删除成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除数据库连接失败，请稍后重试"
        )

@database_router.post("/{connection_id}/test", response_model=DatabaseConnectionTestResponse, summary="测试数据库连接")
async def test_database_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """测试数据库连接"""
    try:
        with get_db_context() as db:
            db_repo = DatabaseConnectionRepository(db)
            
            # 检查数据库连接是否存在
            connection = db_repo.get_by_id(connection_id)
            if not connection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="数据库连接不存在"
                )
            
            # 检查是否属于当前用户
            if connection.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权测试此数据库连接"
                )
            
            # 测试数据库连接 (mock数据) 
            # TODO: 实现数据库连接测试
            is_connected = False
            
            if is_connected:
                logger.info(f"数据库连接测试成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
                return DatabaseConnectionTestResponse(message="数据库连接测试成功", status="success")
            else:
                logger.warning(f"数据库连接测试失败，用户ID: {current_user['id']}, 连接ID: {connection_id}")
                return DatabaseConnectionTestResponse(message="数据库连接测试失败", status="failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试数据库连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="测试数据库连接失败，请稍后重试"
        )
