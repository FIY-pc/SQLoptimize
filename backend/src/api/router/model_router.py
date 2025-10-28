from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from src.schemas.repository.model import CreateModelConnectionReq
from src.api.repository import ModelConnectionRepository
from src.api.utils import get_current_user
from src.api.utils.api_key_utils import mask_api_key
import logging
from src.schemas.params.model import (
    ActiveModelConnectionResponse, 
    SetActiveModelConnectionRequest, 
    SetActiveModelConnectionResponse, 
    ModelConnectionListResponse, 
    ModelConnectionResponse, 
    ModelConnectionUpdate, 
    ModelConnectionCreate
)

logger = logging.getLogger(__name__)

model_router = APIRouter(
    prefix="/api/models",
    tags=["models"],
    responses={404: {"description": "Not found"}},
)

@model_router.get("/active", response_model=ActiveModelConnectionResponse, summary="获取用户当前活跃的模型连接")
async def get_active_model_connection(
    current_user: dict = Depends(get_current_user)
):
    """获取用户当前活跃的模型连接"""
    try:
        model_repo = ModelConnectionRepository()
        active_connection = model_repo.get_active_by_user_id(current_user["id"])
        
        if not active_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户没有任何模型连接"
            )
        
        # 转换为响应模型
        response = ActiveModelConnectionResponse(
            id=active_connection.id,
            model_name=active_connection.model_name,
            model=active_connection.model,
            base_url=active_connection.base_url,
            api_key=mask_api_key(active_connection.api_key),
            model_description=active_connection.model_description,
            model_avatar_url=active_connection.model_avatar_url,
            created_at=active_connection.created_at.isoformat() if active_connection.created_at else "",
            updated_at=active_connection.updated_at.isoformat() if active_connection.updated_at else ""
        )
        
        logger.info(f"获取用户活跃模型连接成功，用户ID: {current_user['id']}, 连接ID: {active_connection.id}, model: {active_connection.model}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户活跃模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活跃模型连接失败，请稍后重试"
        )

@model_router.post("/active", response_model=SetActiveModelConnectionResponse, summary="设置用户当前活跃的模型连接")
async def set_active_model_connection(
    request: SetActiveModelConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """设置用户当前活跃的模型连接"""
    try:
        model_repo = ModelConnectionRepository()
        
        # 设置活跃连接
        success = model_repo.set_active_by_user_id(current_user["id"], request.connection_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型连接不存在或不属于当前用户"
            )
        
        logger.info(f"设置用户活跃模型连接成功，用户ID: {current_user['id']}, 连接ID: {request.connection_id}")
        return SetActiveModelConnectionResponse(message="活跃模型连接设置成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置用户活跃模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置活跃模型连接失败，请稍后重试"
        )

@model_router.get("/", response_model=ModelConnectionListResponse,summary="获取用户模型连接列表")
async def get_user_models(
    skip: int = 0,
    limit: int = 100,
    model: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的模型连接列表"""
    try:
        model_repo = ModelConnectionRepository()
        if model:
            connections = model_repo.get_by_user_and_model(current_user["id"], model)
        else:
            connections = model_repo.get_by_user_id(current_user["id"], skip, limit)
        
        # 转换为响应模型
        model_responses = []
        for conn in connections:
            model_responses.append(ModelConnectionResponse(
                id=conn.id,
                model_name=conn.model_name,
                model=conn.model,
                base_url=conn.base_url,
                api_key=mask_api_key(conn.api_key),
                model_description=conn.model_description,
                model_avatar_url=conn.model_avatar_url,
                created_at=conn.created_at.isoformat() if conn.created_at else "",
                updated_at=conn.updated_at.isoformat() if conn.updated_at else ""
            ))
        
        # 获取总数（用于分页）
        total = model_repo.count_by_user_id(current_user["id"])
        
        # 计算是否还有更多数据
        has_more = (skip + len(model_responses)) < total
        
        # 获取当前用户活跃的模型连接ID
        active_connection = model_repo.get_active_by_user_id(current_user["id"], auto_set_first=True)
        active_connection_id = active_connection.id if active_connection else 0
        
        logger.info(f"获取用户模型连接列表成功，用户ID: {current_user['id']}, 数量: {len(model_responses)}")
        
        return ModelConnectionListResponse(
            models=model_responses,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more,
            active_connection_id=active_connection_id
        )
            
    except Exception as e:
        logger.error(f"获取用户模型连接列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型连接列表失败，请稍后重试"
        )

@model_router.post("/", response_model=ModelConnectionResponse,summary="创建模型连接")
async def create_model_connection(
    request: ModelConnectionCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新的模型连接"""
    try:
        model_repo = ModelConnectionRepository()
            
        # 检查模型名称是否已存在
        if model_repo.exists_by_name(request.model_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型名称已存在"
            )
        
        # 创建模型连接
        connection_data = CreateModelConnectionReq(
            model_name=request.model_name,
            model=request.model,
            base_url=request.base_url,
            api_key=request.api_key,
            model_description=request.model_description,
            model_avatar_url=request.model_avatar_url,
            user_id=current_user["id"]
        )
        
        connection = model_repo.create(connection_data)
        
        # 转换为响应模型
        response = ModelConnectionResponse(
            id=connection.id,
            model_name=connection.model_name,
            model=connection.model,
            base_url=connection.base_url,
            api_key=mask_api_key(connection.api_key),
            model_description=connection.model_description,
            model_avatar_url=connection.model_avatar_url,
            created_at=connection.created_at.isoformat() if connection.created_at else "",
            updated_at=connection.updated_at.isoformat() if connection.updated_at else ""
        )
        
        logger.info(f"创建模型连接成功，用户ID: {current_user['id']}, 模型名称: {connection.model_name}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建模型连接失败，请稍后重试"
        )

@model_router.get("/{connection_id}", response_model=ModelConnectionResponse,summary="根据ID获取模型连接")
async def get_model_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取指定的模型连接信息"""
    try:
        model_repo = ModelConnectionRepository()
        connection = model_repo.get_by_id(connection_id)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型连接不存在"
            )
        
        # 检查是否属于当前用户
        if connection.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此模型连接"
            )
        
        # 转换为响应模型
        response = ModelConnectionResponse(
            id=connection.id,
            model_name=connection.model_name,
            model=connection.model,
            base_url=connection.base_url,
            api_key=mask_api_key(connection.api_key),
            model_description=connection.model_description,
            model_avatar_url=connection.model_avatar_url,
            created_at=connection.created_at.isoformat() if connection.created_at else "",
            updated_at=connection.updated_at.isoformat() if connection.updated_at else ""
        )
        
        logger.info(f"获取模型连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型连接失败，请稍后重试"
        )

@model_router.put("/{connection_id}", response_model=ModelConnectionResponse,summary="更新模型连接")
async def update_model_connection(
    connection_id: int,
    request: ModelConnectionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新模型连接信息"""
    try:
        model_repo = ModelConnectionRepository()
            
        # 检查模型连接是否存在
        connection = model_repo.get_by_id(connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型连接不存在"
            )
        
        # 检查是否属于当前用户
        if connection.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此模型连接"
            )
        
        # 如果更新模型名称，检查是否与其他连接冲突
        if request.model_name and request.model_name != connection.model_name:
            if model_repo.exists_by_name(request.model_name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="模型名称已存在"
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
        
        # 更新模型连接
        updated_connection = model_repo.update(connection_id, update_data)
        
        # 转换为响应模型
        response = ModelConnectionResponse(
            id=updated_connection.id,
            model_name=updated_connection.model_name,
            model=updated_connection.model,
            base_url=updated_connection.base_url,
            api_key=mask_api_key(updated_connection.api_key),
            model_description=updated_connection.model_description,
            model_avatar_url=updated_connection.model_avatar_url,
            created_at=updated_connection.created_at.isoformat() if updated_connection.created_at else "",
            updated_at=updated_connection.updated_at.isoformat() if updated_connection.updated_at else ""
        )
        
        logger.info(f"更新模型连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新模型连接失败，请稍后重试"
        )

@model_router.delete("/{connection_id}",summary="删除模型连接")
async def delete_model_connection(
    connection_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除模型连接"""
    try:
        model_repo = ModelConnectionRepository()
            
        # 检查模型连接是否存在
        connection = model_repo.get_by_id(connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型连接不存在"
            )
        
        # 检查是否属于当前用户
        if connection.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此模型连接"
            )
        
        # 删除模型连接
        success = model_repo.delete(connection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除模型连接失败"
            )
        
        logger.info(f"删除模型连接成功，用户ID: {current_user['id']}, 连接ID: {connection_id}")
        return {"message": "模型连接删除成功"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模型连接失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除模型连接失败，请稍后重试"
        )