from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import json
from .pipelines import execute_pipeline_api, execute_pipeline_stream

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
        final_state = await execute_pipeline_api(req.sql)
        return OptimizeResponse(
            input_sql=final_state.get("input_sql") or "",
            optimized_sql=final_state.get("optimized_sql"),
            plan_feedback=final_state.get("plan_feedback"),
            history=final_state.get("history") or [],
        )

# 流式输出的响应模型，只包含必要字段
class StreamResponse(BaseModel):
    node_name: str = ""
    input_sql: str = ""
    optimized_sql: str = ""
    plan_feedback: str = ""
    history: List[str] = []

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
                node_name, node_data = list(chunk.items())[0]
                if isinstance(node_data, dict):
                    node_data['node_name'] = node_name
                    filtered_response = StreamResponse(**node_data)
                else:
                    raise HTTPException(status_code=500, detail=f"Invalid node data: {node_data}")

                # SSE 协议每条消息以 data: 开头，\n\n 结尾
                yield f"data: {json.dumps(filtered_response.model_dump(), ensure_ascii=False)}\n\n"
            except Exception as model_error:
                raise HTTPException(status_code=500, detail=str(model_error))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))