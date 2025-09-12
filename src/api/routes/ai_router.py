from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
from src.pipelines import execute_pipeline_api, execute_pipeline_stream
from src.api.utils import get_unix_timestamp
import logging
from pydantic import BaseModel
from typing import List, Literal, Union, Optional

"""日志配置"""
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""路由配置"""
ai_router = APIRouter(
    prefix="/api",
    tags=["AI"],
    responses={404: {"description": "Not found"}},
)

"""请求和响应模型"""

class OptimizeRequest(BaseModel):
    sql: str
    db_schema: Optional[str] = ""
    stream: bool = False          # 是否流式输出
    stream_llm_chunk: Optional[bool] = True # 是否流式输出 LLM 的 chunk

class OptimizeResponse(BaseModel):
    input_sql: str
    optimized_sql: str = ""
    plan_feedback: str = ""
    db_schema: str = ""
    z3_result: List[str] = []
    history: List[str] = []
    timestamp: int = 0

# 流式输出的响应模型，只包含必要字段
class NodeChunk(BaseModel):
    type: str = "data"
    node_name: str = ""
    input_sql: str = ""
    optimized_sql: str = ""
    plan_feedback: str = ""
    db_schema: str = ""
    z3_result: List[str] = []
    history: List[str] = []

class ErrorChunk(BaseModel):
    error: str = ""

class Chunk(BaseModel):
    type: Literal["node_chunk", "llm_chunk", "error_chunk"] = "node_chunk"
    data: Union[NodeChunk, str, ErrorChunk]
    timestamp: int = 0

"""路由handler"""

@ai_router.post("/optimize")
async def optimize(req: OptimizeRequest):
    if req.stream:
        # 流式响应
        try:
            return StreamingResponse(gen_stream_sse(req), media_type="text/event-stream")
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
            history=final_state.get("history") or [],
            timestamp=get_unix_timestamp()
        )

# 辅助函数，生成标准的 SSE 流
async def gen_stream_sse(req: OptimizeRequest):
    try:
        queue = asyncio.Queue()

        # 一个回调函数，用于流式输出 LLM 的 chunk给前端
        def on_chunk(llm_chunk):
            if llm_chunk is None:
                queue.put_nowait(None)
                return

            if isinstance(llm_chunk, str):
                llm_chunk = llm_chunk.strip()
            else:
                if hasattr(llm_chunk, 'dict'):
                    llm_chunk = llm_chunk.dict()
                elif isinstance(llm_chunk, dict):
                    pass  # use as is
                elif hasattr(llm_chunk, '__dict__'):
                    llm_chunk = llm_chunk.__dict__
                else:
                    try:
                        llm_chunk = json.loads(llm_chunk)
                    except Exception:
                        logger.error(f"Cannot convert llm_chunk to dict: {llm_chunk}")

            data = Chunk(
                type="llm_chunk", 
                data=llm_chunk, 
                timestamp=get_unix_timestamp()
            )
            queue.put_nowait(data)

        # 执行流式输出
        async def run_pipeline_stream():
            try:
                async for chunk in execute_pipeline_stream(
                    sql=req.sql, 
                    on_chunk=on_chunk if req.stream_llm_chunk else None,
                    db_schema=req.db_schema or ""
                ):
                    # 处理 LangGraph 节点输出
                    if not isinstance(chunk, dict):
                        if hasattr(chunk, 'dict'):
                            chunk = chunk.dict()
                        elif hasattr(chunk, '__dict__'):
                            chunk = chunk.__dict__
                        else:
                            chunk = json.loads(chunk)

                    # LangGraph 流式输出结构: {"节点名": State}
                    node_name, node_data = list(chunk.items())[0]
                    if isinstance(node_data, dict):
                        node_data['node_name'] = node_name
                        filtered_response = NodeChunk(**node_data)
                        data = Chunk(
                            type="node_chunk", 
                            data=filtered_response, 
                            timestamp=get_unix_timestamp()
                        )
                        
                        # 节点完成时的输出
                        queue.put_nowait(data)
                    else:
                        logger.error(f"Invalid node data: {node_data}")
                        data = Chunk(
                            type="error_chunk", 
                            data=ErrorChunk(error=f"Invalid node data: {node_data}"), 
                            timestamp=get_unix_timestamp()
                        )
                        queue.put_nowait(data)
                        return
            except Exception as e:
                logger.error(f"Error in run_pipeline_stream: {e}")
                data = Chunk(
                    type="error_chunk", 
                    data=ErrorChunk(error=str(e)), 
                    timestamp=get_unix_timestamp()
                )
                queue.put_nowait(data)
            finally:
                # 标记结束
                queue.put_nowait(None)

        pipeline_task = asyncio.create_task(run_pipeline_stream())
        while True:
            item = await queue.get()
            if item is None:
                break
            # 格式化为 SSE
            yield f"data: {json.dumps(item.model_dump(), ensure_ascii=False)}\n\n"
        await pipeline_task

    except Exception as e:
        logger.error(f"Error in gen_stream_sse: {e}")
        data = Chunk(
            type="error_chunk", 
            data=ErrorChunk(error=str(e)), 
            timestamp=get_unix_timestamp()
        )
        yield f"data: {json.dumps(data.model_dump(), ensure_ascii=False)}\n\n"
        return