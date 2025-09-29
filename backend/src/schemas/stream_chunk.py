from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional

ChunkType = Literal["node_chunk", "llm_chunk", "error_chunk"]

class NodeChunk(BaseModel):
    node_name: str = Field(default="", description="节点名称")
    input_sql: str = Field(default="", description="输入 SQL")
    optimized_sql: str = Field(default="", description="优化后 SQL")    
    plan_feedback: str = Field(default="", description="执行计划或静态分析反馈")    
    db_schema: str = Field(default="", description="数据库 schema")
    z3_result: List[str] = Field(default=[], description="Z3 验证结果")
    history: List[str] = Field(default=[], description="历史轨迹")

class LLMChunk(BaseModel):
    content: Optional[str] = Field(default="", description="内容")
class ErrorChunk(BaseModel):
    error: Optional[str] = Field(default="", description="错误信息")

class Chunk(BaseModel):
    type: ChunkType = Field(default="node_chunk", description="类型")
    data: Union[NodeChunk, LLMChunk, ErrorChunk] = Field(..., description="数据")
    timestamp: int = Field(default=0, description="时间戳")