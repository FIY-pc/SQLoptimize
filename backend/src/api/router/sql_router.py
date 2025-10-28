import logging
from fastapi import APIRouter
from src.api.utils import get_current_user
from src.schemas.params.sql import RunRequest, RunResponse
from fastapi import Depends, HTTPException
from src.api.repository import DatabaseConnectionRepository
from src.db.registry import DatabaseRegistry
from src.utils.time_utils import get_unix_timestamp
from sqlalchemy import text 
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
        async with registry.async_session() as session:
            result = await session.execute(text(req.sql))
            rows = result.fetchall()
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
            
            return RunResponse(
                success=True,
                result=result_data,
                timestamp=get_unix_timestamp(),
            )
    except Exception as e:
        logger.error(f"Error in run_sql: {e}")
        return RunResponse(
            success=False,
            error=str(e),
            timestamp=get_unix_timestamp(),
            result=[],
        )