from pydantic import BaseModel, Field
from typing import Optional, List

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