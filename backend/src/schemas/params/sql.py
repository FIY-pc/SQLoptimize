from pydantic import BaseModel, Field
from typing import List, Any
class RunRequest(BaseModel):
    sql: str = Field(..., description="SQL语句")

class RunResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    result: List[Any] = Field(default=[], description="执行结果")
    timestamp: int = Field(default=0, description="时间戳")
    error: str = Field(default="", description="错误信息")