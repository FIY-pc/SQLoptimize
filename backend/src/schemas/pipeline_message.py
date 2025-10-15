from pydantic import BaseModel, Field
from typing import Literal, Optional
from langchain_core.messages import AIMessageChunk


class PipelineMessage(BaseModel):
    """管道消息基类"""
    type: Literal["error", "end", "info"] = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    timestamp: int = Field(..., description="时间戳")


class ErrorMessage(PipelineMessage):
    """错误消息"""
    type: Literal["error"] = "error"


class EndMessage(PipelineMessage):
    """结束消息"""
    type: Literal["end"] = "end"


class InfoMessage(PipelineMessage):
    """信息消息"""
    type: Literal["info"] = "info"


def create_error_message(content: str, timestamp: int) -> AIMessageChunk:
    """创建错误消息的 AIMessageChunk"""
    error_msg = ErrorMessage(content=content, timestamp=timestamp)
    return AIMessageChunk(content=error_msg.model_dump_json())


def create_end_message(content: str, timestamp: int) -> AIMessageChunk:
    """创建结束消息的 AIMessageChunk"""
    end_msg = EndMessage(content=content, timestamp=timestamp)
    return AIMessageChunk(content=end_msg.model_dump_json())


def create_info_message(content: str, timestamp: int) -> AIMessageChunk:
    """创建信息消息的 AIMessageChunk"""
    info_msg = InfoMessage(content=content, timestamp=timestamp)
    return AIMessageChunk(content=info_msg.model_dump_json())
