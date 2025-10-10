from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.pipelines import execute_pipeline_api, execute_pipeline_stream
from src.utils import get_unix_timestamp
import logging
from pydantic import BaseModel, Field
from typing import List, Optional
from src.stream.stream_writer import StreamWriter
from src.schemas.stream_chunk import Chunk

"""日志"""
logger = logging.getLogger(__name__)

"""路由配置"""
ai_router = APIRouter(
    prefix="/api",
    tags=["ai"],
    responses={404: {"description": "Not found"}},
)

"""请求和响应模型"""

class OptimizeRequest(BaseModel):
    sql: str = Field(..., description="SQL语句")
    db_schema: Optional[str] = Field(default="", description="数据库 schema")
    stream: bool = Field(default=False, description="是否流式输出")          # 是否流式输出
    stream_llm_chunk: Optional[bool] = Field(default=True, description="是否流式输出 LLM 的 chunk") # 是否流式输出 LLM 的 chunk

class OptimizeResponse(BaseModel):
    input_sql: str = Field(..., description="输入 SQL")
    optimized_sql: str = Field(default="", description="优化后 SQL")
    plan_feedback: str = Field(default="", description="执行计划或静态分析反馈")
    db_schema: str = Field(default="", description="数据库 schema")
    z3_result: List[str] = Field(default=[], description="Z3 验证结果")
    # history: List[str] = Field(default=[], description="历史轨迹")
    timestamp: int = Field(default=0, description="时间戳")
    
"""路由handler"""

@ai_router.post("/optimize",summary="调用agent优化SQL")
async def optimize(req: OptimizeRequest):
    if req.stream:
        # 流式响应
        try:
            return StreamingResponse(gen_stream(req), media_type="text/event-stream")
        except Exception as e:
            logger.error(f"Error in optimize: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 非流式响应
        try:
            final_state = await execute_pipeline_api(req.sql, req.db_schema)
        except Exception as e:
            logger.error(f"Error in optimize: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        return OptimizeResponse(
            input_sql=final_state.get("input_sql") or "",
            optimized_sql=final_state.get("optimized_sql"),
            plan_feedback=final_state.get("plan_feedback"),
            db_schema=final_state.get("db_schema") or "",
            z3_result=final_state.get("z3_result") or [],
            # history=final_state.get("history") or [],
            timestamp=get_unix_timestamp()
        )

async def gen_stream(req: OptimizeRequest):
    stream_writer = StreamWriter()
    pipeline_task = None
    
    try:
        # 启动后台任务处理管道输出
        async def process_pipeline():
            try:
                async for message_chunk, metadata in execute_pipeline_stream(
                    sql=req.sql, 
                    db_schema=req.db_schema or ""
                ):
                    message_chunk_dict = message_chunk.model_dump()
                    chunk = Chunk(
                        metadata=metadata,
                        **message_chunk_dict
                    )
                    await stream_writer.write(chunk)
            except Exception as e:
                logger.error(f"Error in process_pipeline: {e}")
                await stream_writer.error(str(e))
            finally:
                await stream_writer.close()
        
        # 启动后台任务
        import asyncio
        pipeline_task = asyncio.create_task(process_pipeline())
        
        # 流式输出数据
        async for chunk in stream_writer.stream():
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in gen_stream: {e}")
        # 确保在出错时也关闭流
        await stream_writer.close()
        raise
    finally:
        # 确保后台任务完成和资源清理
        try:
            if pipeline_task and not pipeline_task.done():
                # 等待任务完成，最多等待3秒
                await asyncio.wait_for(pipeline_task, timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Pipeline task timeout, cancelling...")
            if pipeline_task:
                pipeline_task.cancel()
                try:
                    await pipeline_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Error waiting for pipeline task: {e}")
            if pipeline_task:
                pipeline_task.cancel()
                try:
                    await pipeline_task
                except asyncio.CancelledError:
                    pass
        finally:
            # 确保资源清理
            await stream_writer.cleanup()
            logger.debug("Stream resources cleaned up")