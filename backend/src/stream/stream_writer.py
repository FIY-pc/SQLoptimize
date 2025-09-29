import asyncio
import json
import logging
from typing import AsyncIterator
from src.schemas.stream_chunk import Chunk, ErrorChunk
from src.utils import get_unix_timestamp

logger = logging.getLogger(__name__)

class StreamWriter:
    """
    流式输出写入器
    通过传递 StreamWriter 对象，可以在任意位置向流中写入数据
    """
    def __init__(self):
        self._queue = asyncio.Queue()
        self._closed = False

    async def write(self, data: Chunk):
        """向流式输出中写入数据"""
        await self._queue.put(data)

    async def close(self):
        """关闭流式输出"""
        self._closed = True
        await self._queue.put(None)  # 用 None 作为结束标记
    
    async def error(self, error: str):
        """在流式输出中抛出错误"""
        logger.error(f"Error in StreamWriter: {error}")
        error_chunk = ErrorChunk(error=str(error))
        data = Chunk(
            type="error_chunk", 
            data=error_chunk, 
            timestamp=get_unix_timestamp()
        )
        await self._queue.put(data)
        await self.close()

    async def stream(self) -> AsyncIterator[str]:
        """流式输出数据"""
        while not self._closed:
            try:
                item = await self._queue.get()
                if item is None:
                    break  # 遇到结束标记，退出循环
                yield self.wrap_sse(item)
            except Exception as e:
                logger.error(f"Error in stream: {e}")
                await self.error(str(e))
                break

    def wrap_sse(self, data: Chunk) -> str:
        """将数据包装为 SSE 格式"""
        try:
            data = data.model_dump()
        except Exception:
            try:
                data = json.loads(data)
            except Exception:
                logger.error(f"Invalid data: {data}, type: {type(data)}")
                raise ValueError(f"Invalid data: {data}, type: {type(data)}")
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"