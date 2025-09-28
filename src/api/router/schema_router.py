from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional
from src.api.repository.db_schema_repository import DbSchemaRepository
from src.api.utils import get_current_user
import logging
import uuid
    
logger = logging.getLogger(__name__)

schema_router = APIRouter(
    prefix="/api/schemas",
    tags=["schemas"],
    responses={404: {"description": "Not found"}},
)

# 请求和响应模型
class DbSchemaCreate(BaseModel):
    """创建数据库模式请求"""
    schema_name: Optional[str] = Field(default=None, description="模式名称，不提供则自动生成UUID")
    schema_content: str = Field(..., description="模式内容（JSON字符串）")

class DbSchemaUpdate(BaseModel):
    """更新数据库模式请求"""
    schema_name: Optional[str] = Field(default=None, description="模式名称")
    schema_content: Optional[str] = Field(default=None, description="模式内容（JSON字符串）")

class DbSchemaResponse(BaseModel):
    """数据库模式响应"""
    id: int = Field(..., description="模式ID")
    schema_name: str = Field(..., description="模式名称")
    schema_content: str = Field(..., description="模式内容")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    user_id: int = Field(..., description="用户ID")

    class Config:
        from_attributes = True

class DbSchemaListResponse(BaseModel):
    """数据库模式列表响应"""
    schemas: List[DbSchemaResponse] = Field(..., description="模式列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="限制数量")
    active_schema_id: int = Field(0, description="当前用户活跃的数据库模式ID，0表示无活跃模式")

class DbSchemaDeleteResponse(BaseModel):
    """数据库模式删除响应"""
    message: str = Field(..., description="删除结果消息")

class ActiveDbSchemaResponse(BaseModel):
    """活跃数据库模式响应"""
    id: int = Field(..., description="模式ID")
    schema_name: str = Field(..., description="模式名称")
    schema_content: str = Field(..., description="模式内容")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    user_id: int = Field(..., description="用户ID")

    class Config:
        from_attributes = True

class SetActiveDbSchemaRequest(BaseModel):
    """设置活跃数据库模式请求"""
    schema_id: int = Field(..., description="模式ID")

class SetActiveDbSchemaResponse(BaseModel):
    """设置活跃数据库模式响应"""
    message: str = Field(..., description="设置结果消息")

@schema_router.get("/active", response_model=ActiveDbSchemaResponse, summary="获取用户当前活跃的数据库模式")
async def get_active_db_schema(
    current_user: dict = Depends(get_current_user)
):
    """获取用户当前活跃的数据库模式"""
    try:
        schema_repo = DbSchemaRepository()
        active_schema = schema_repo.get_active_by_user_id(current_user["id"])
        
        if not active_schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户没有任何数据库模式"
            )
        
        # 转换为响应模型
        response = ActiveDbSchemaResponse(
            id=active_schema.id,
            schema_name=active_schema.schema_name,
            schema_content=active_schema.schema_content,
            created_at=active_schema.created_at.isoformat() if active_schema.created_at else "",
            updated_at=active_schema.updated_at.isoformat() if active_schema.updated_at else "",
            user_id=active_schema.user_id
        )
        
        logger.info(f"获取用户活跃数据库模式成功，用户ID: {current_user['id']}, 模式ID: {active_schema.id}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户活跃数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活跃数据库模式失败，请稍后重试"
        )

@schema_router.post("/active", response_model=SetActiveDbSchemaResponse, summary="设置用户当前活跃的数据库模式")
async def set_active_db_schema(
    request: SetActiveDbSchemaRequest,
    current_user: dict = Depends(get_current_user)
):
    """设置用户当前活跃的数据库模式"""
    try:
        schema_repo = DbSchemaRepository()
        
        # 设置活跃模式
        success = schema_repo.set_active_by_user_id(current_user["id"], request.schema_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据库模式不存在或不属于当前用户"
            )
        
        logger.info(f"设置用户活跃数据库模式成功，用户ID: {current_user['id']}, 模式ID: {request.schema_id}")
        return SetActiveDbSchemaResponse(message="活跃数据库模式设置成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置用户活跃数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置活跃数据库模式失败，请稍后重试"
        )

@schema_router.get("/", response_model=DbSchemaListResponse, summary="获取用户数据库模式列表")
async def get_user_schemas(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的数据库模式列表"""
    try:
        schema_repo = DbSchemaRepository()
        schemas = schema_repo.get_by_user_id(current_user["id"], skip, limit)
        
        # 转换为响应模型
        schema_responses = []
        for schema in schemas:
            schema_responses.append(DbSchemaResponse(
                id=schema.id,
                schema_name=schema.schema_name,
                schema_content=schema.schema_content,
                created_at=schema.created_at.isoformat() if schema.created_at else "",
                updated_at=schema.updated_at.isoformat() if schema.updated_at else "",
                user_id=schema.user_id
            ))
        
        # 获取总数（用于分页）
        total_schemas = schema_repo.get_by_user_id(current_user["id"], 0, 1000)
        total = len(total_schemas)
        
        # 获取当前用户活跃的数据库模式ID
        active_schema = schema_repo.get_active_by_user_id(current_user["id"], auto_set_first=True)
        active_schema_id = active_schema.id if active_schema else 0
        
        logger.info(f"获取用户数据库模式列表成功，用户ID: {current_user['id']}, 数量: {len(schema_responses)}")
        
        return DbSchemaListResponse(
            schemas=schema_responses,
            total=total,
            skip=skip,
            limit=limit,
            active_schema_id=active_schema_id
        )
            
    except Exception as e:
        logger.error(f"获取用户数据库模式列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库模式列表失败，请稍后重试"
        )

@schema_router.post("/", response_model=DbSchemaResponse, summary="创建数据库模式")
async def create_db_schema(
    request: DbSchemaCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新的数据库模式"""
    try:
        schema_repo = DbSchemaRepository()
        
        # 如果没有提供 schema_name，则自动生成 UUID
        schema_name = request.schema_name
        if not schema_name:
            schema_name = str(uuid.uuid4())
        
        # 检查模式名称是否已存在（如果提供了自定义名称）
        if request.schema_name and schema_repo.exists_by_name(schema_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模式名称已存在"
            )
        
        # 创建数据库模式
        schema_data = {
            "schema_name": schema_name,
            "schema_content": request.schema_content,
            "user_id": current_user["id"]
        }
        
        schema = schema_repo.create(schema_data)
        
        # 转换为响应模型
        response = DbSchemaResponse(
            id=schema.id,
            schema_name=schema.schema_name,
            schema_content=schema.schema_content,
            created_at=schema.created_at.isoformat() if schema.created_at else "",
            updated_at=schema.updated_at.isoformat() if schema.updated_at else "",
            user_id=schema.user_id
        )
        
        logger.info(f"创建数据库模式成功，用户ID: {current_user['id']}, 模式名称: {schema.schema_name}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建数据库模式失败，请稍后重试"
        )

@schema_router.get("/{schema_id}", response_model=DbSchemaResponse, summary="根据ID获取数据库模式")
async def get_db_schema(
    schema_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取指定的数据库模式信息"""
    try:
        schema_repo = DbSchemaRepository()
        schema = schema_repo.get_by_id(schema_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据库模式不存在"
            )
        
        # 检查是否属于当前用户
        if schema.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此数据库模式"
            )
        
        # 转换为响应模型
        response = DbSchemaResponse(
            id=schema.id,
            schema_name=schema.schema_name,
            schema_content=schema.schema_content,
            created_at=schema.created_at.isoformat() if schema.created_at else "",
            updated_at=schema.updated_at.isoformat() if schema.updated_at else "",
            user_id=schema.user_id
        )
        
        logger.info(f"获取数据库模式成功，用户ID: {current_user['id']}, 模式ID: {schema_id}")
        return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据库模式失败，请稍后重试"
        )

@schema_router.put("/{schema_id}", response_model=DbSchemaResponse, summary="更新数据库模式")
async def update_db_schema(
    schema_id: int,
    request: DbSchemaUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新数据库模式信息"""
    try:
        schema_repo = DbSchemaRepository()
        
        # 检查数据库模式是否存在
        schema = schema_repo.get_by_id(schema_id)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据库模式不存在"
            )
        
        # 检查是否属于当前用户
        if schema.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此数据库模式"
            )
        
        # 如果更新模式名称，检查是否与其他模式冲突
        if request.schema_name and request.schema_name != schema.schema_name:
            if schema_repo.exists_by_name(request.schema_name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="模式名称已存在"
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
        
        # 更新数据库模式
        updated_schema = schema_repo.update(schema_id, update_data)
        
        # 转换为响应模型
        response = DbSchemaResponse(
            id=updated_schema.id,
            schema_name=updated_schema.schema_name,
            schema_content=updated_schema.schema_content,
            created_at=updated_schema.created_at.isoformat() if updated_schema.created_at else "",
            updated_at=updated_schema.updated_at.isoformat() if updated_schema.updated_at else "",
            user_id=updated_schema.user_id
        )
        
        logger.info(f"更新数据库模式成功，用户ID: {current_user['id']}, 模式ID: {schema_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新数据库模式失败，请稍后重试"
        )

@schema_router.delete("/{schema_id}", response_model=DbSchemaDeleteResponse, summary="删除数据库模式")
async def delete_db_schema(
    schema_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除数据库模式"""
    try:
        schema_repo = DbSchemaRepository()
        
        # 检查数据库模式是否存在
        schema = schema_repo.get_by_id(schema_id)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据库模式不存在"
            )
        
        # 检查是否属于当前用户
        if schema.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此数据库模式"
            )
        
        # 删除数据库模式
        success = schema_repo.delete(schema_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除数据库模式失败"
            )
        
        logger.info(f"删除数据库模式成功，用户ID: {current_user['id']}, 模式ID: {schema_id}")
        return DbSchemaDeleteResponse(message="数据库模式删除成功")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除数据库模式失败，请稍后重试"
        )