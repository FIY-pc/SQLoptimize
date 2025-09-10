from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json
import time
from .pipelines import execute_pipeline_api, execute_pipeline_stream
from .utils import get_unix_timestamp

app = FastAPI(title="SQLoptimize API", version="0.1.0")

# 允许本地前端跨域调试（按需收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class OptimizeRequest(BaseModel):
    sql: str
    stream: bool = False

class OptimizeResponse(BaseModel):
    input_sql: str
    optimized_sql: str = ""
    plan_feedback: str = ""
    history: List[str] = []
    timestamp: int = 0

@app.get("/api/ping")
async def ping():
    return {"status": "ok"}

@app.post("/api/optimize")
async def optimize(req: OptimizeRequest):
    if req.stream:
        # 流式响应
        try:
            return StreamingResponse(gen_stream_sse(req), media_type="text/event-stream")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 非流式响应
        try:
            final_state = await execute_pipeline_api(req.sql)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        return OptimizeResponse(
            input_sql=final_state.get("input_sql") or "",
            optimized_sql=final_state.get("optimized_sql"),
            plan_feedback=final_state.get("plan_feedback"),
            history=final_state.get("history") or [],
            timestamp=get_unix_timestamp()
        )
        
# 流式输出的响应模型，只包含必要字段
class StreamResponse(BaseModel):
    type: str = "data"
    node_name: str = ""
    input_sql: str = ""
    optimized_sql: str = ""
    plan_feedback: str = ""
    history: List[str] = []
    error: str = ""
    timestamp: int = 0

# 辅助函数，生成标准的 SSE 流
async def gen_stream_sse(req: OptimizeRequest):
    try:
        async for chunk in execute_pipeline_stream(req.sql):
            # 转成 dict
            if not isinstance(chunk, dict):
                if hasattr(chunk, 'dict'):
                    chunk = chunk.dict()
                elif hasattr(chunk, '__dict__'):
                    chunk = chunk.__dict__
                else:
                    chunk = json.loads(chunk)
            try:
                # LangGraph 流式输出结构: {"节点名": State}
                timestamp = get_unix_timestamp()
                node_name, node_data = list(chunk.items())[0]
                if isinstance(node_data, dict):
                    node_data['node_name'] = node_name
                    node_data['timestamp'] = timestamp
                    filtered_response = StreamResponse(**node_data)
                else:
                    error_response = StreamResponse(type="error", error=f"Invalid node data: {node_data}", timestamp=timestamp)
                    yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"
                    return

                # SSE 协议每条消息以 data: 开头，\n\n 结尾
                yield f"data: {json.dumps(filtered_response.model_dump(), ensure_ascii=False)}\n\n"
            except Exception as model_error:
                timestamp = get_unix_timestamp()
                error_response = StreamResponse(type="error", error=str(model_error), timestamp=timestamp)
                yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"
                return
    except Exception as e:
        timestamp = get_unix_timestamp()
        error_response = StreamResponse(type="error", error=str(e), timestamp=timestamp)
        yield f"data: {json.dumps(error_response.model_dump(), ensure_ascii=False)}\n\n"
        return