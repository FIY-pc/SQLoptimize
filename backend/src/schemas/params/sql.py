from pydantic import BaseModel, Field, field_validator
from typing import List, Any
class RunRequest(BaseModel):
    sql: str = Field(..., description="SQL语句")
    page: int = Field(default=1, description="页码，从1开始", ge=1)
    page_size: int = Field(default=100, description="每页记录数", ge=1, le=1000)
    include_total: bool = Field(default=False, description="是否计算总记录数（大数据集可能较慢，默认false以提高性能）")

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """限制每页最大记录数，防止大页攻击"""
        if v > 1000:
            return 1000
        return v

class RunResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    result: List[Any] = Field(default=[], description="执行结果")
    timestamp: int = Field(default=0, description="时间戳")
    cost_time: float = Field(default=0, description="执行时间")
    error: str = Field(default="", description="错误信息")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=100, description="每页记录数")
    total: int = Field(default=0, description="总记录数，-1表示未知（未计算总数以提高性能）")
    total_pages: int = Field(default=0, description="总页数，-1表示未知")