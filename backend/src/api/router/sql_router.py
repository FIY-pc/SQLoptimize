import logging
from fastapi import APIRouter
from src.api.utils import get_current_user
from src.api.utils.sql_utils import add_pagination_to_sql, get_count_sql
from src.schemas.params.sql import RunRequest, RunResponse
from fastapi import Depends, HTTPException
from src.api.repository import DatabaseConnectionRepository
from src.db.registry import DatabaseRegistry
from src.utils.time_utils import get_unix_timestamp
from sqlalchemy import text 
import time
logger = logging.getLogger(__name__)

sql_router = APIRouter(
    prefix="/api/sqls",
    tags=["sqls"],
    responses={404: {"description": "Not found"}},
)

@sql_router.post("/run", response_model=RunResponse, summary="运行SQL")
async def run_sql(
    req: RunRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        database_repo = DatabaseConnectionRepository()
        database_connection = database_repo.get_active_by_user_id(current_user["id"])
        if not database_connection:
            raise HTTPException(status_code=400, detail="数据库连接不存在")
        registry = DatabaseRegistry(database_connection.database_uri)
        
        # 获取数据库类型（从connection对象获取，如果不存在则从URI检测）
        database_type = database_connection.database_type
        if not database_type:
            # 如果connection中没有类型，从URI检测
            from urllib.parse import urlparse
            parsed = urlparse(database_connection.database_uri)
            scheme = parsed.scheme.lower()
            if scheme.startswith('sqlite'):
                database_type = 'sqlite'
            elif scheme.startswith('postgres'):
                database_type = 'postgresql'
            elif scheme.startswith('mysql'):
                database_type = 'mysql'
            else:
                database_type = 'unknown'
        
        # 在数据库层面添加分页限制，防止大查询攻击(虽然也并非很好的手段，只能相信数据库的optimizer了)
        page = req.page
        page_size = min(req.page_size, 1000)  # 确保不超过最大限制
        
        # 将原SQL包装在子查询中，添加LIMIT和OFFSET
        # 这样数据库只会执行实际查询并返回指定页的数据，而不是所有数据
        paginated_sql = add_pagination_to_sql(req.sql, page, page_size, database_type)
        
        
        async with registry.async_session() as session:
            begin_time = time.time()
            # 执行分页后的SQL查询，数据库只会返回指定页的数据
            result = await session.execute(text(paginated_sql))
            rows = result.fetchall()
            end_time = time.time()

            # 将 SQLAlchemy Row 对象转换为字典列表
            result_data = []
            for row in rows:
                if hasattr(row, '_asdict'):
                    # 如果是 Row 对象，转换为字典
                    result_data.append(row._asdict())
                elif hasattr(row, '__dict__'):
                    # 如果是其他对象，尝试获取属性
                    result_data.append(row.__dict__)
                else:
                    # 如果是元组或其他类型，直接转换
                    result_data.append(list(row))
            
            # 根据请求参数决定是否计算总数
            
            if req.include_total:
                try:
                    count_sql = get_count_sql(req.sql)
                    count_result = await session.execute(text(count_sql))
                    total = count_result.scalar() or 0
                    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
                except Exception as count_error:
                    logger.warning(f"Failed to get total count: {count_error}")
                    total = -1
                    total_pages = -1
            else:
                # 不计算总数，设置为-1表示未知
                total = -1
                total_pages = -1
            
            cost_time = end_time - begin_time
            return RunResponse(
                success=True,
                result=result_data,
                timestamp=get_unix_timestamp(),
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                cost_time=cost_time,
            )
    except Exception as e:
        logger.error(f"Error in run_sql: {e}")
        return RunResponse(
            success=False,
            error=str(e),
            timestamp=get_unix_timestamp(),
            result=[],
            page=req.page,
            page_size=req.page_size,
            total=0,
            total_pages=0,
            cost_time=0,
        )