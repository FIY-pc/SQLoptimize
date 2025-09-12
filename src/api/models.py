from pydantic import BaseModel
from typing import List, Literal, Union, Optional
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