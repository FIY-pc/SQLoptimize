from langchain_core.messages import AIMessageChunk


def create_error_message(error: str, timestamp: int) -> AIMessageChunk:
    """创建标准错误消息块，便于前端统一处理"""
    return AIMessageChunk(
        content=error,
        additional_kwargs={
            "type": "error",
            "timestamp": timestamp,
        },
    )


def create_end_message(status: str, timestamp: int) -> AIMessageChunk:
    """创建结束标记消息块（非 [DONE] 控制标记，走数据通道）"""
    return AIMessageChunk(
        content=status,
        additional_kwargs={
            "type": "end",
            "timestamp": timestamp,
        },
    )
