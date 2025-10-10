import asyncio
import json
import logging
from typing import AsyncIterator
from src.schemas.stream_chunk import Chunk
from src.utils import get_unix_timestamp
from langchain_core.messages import AIMessageChunk

logger = logging.getLogger(__name__)

class StreamWriter:
    """
    流式输出写入器
    通过传递 StreamWriter 对象，可以在任意位置向流中写入数据
    """
    def __init__(self):
        self._queue = asyncio.Queue()
        self._closed = False
        self._error_occurred = False
        self._cleanup_done = False

    async def write(self, data: Chunk):
        """向流式输出中写入数据"""
        if not self._closed and not self._error_occurred:
            await self._queue.put(data)

    async def close(self):
        """关闭流式输出"""
        if not self._closed:
            self._closed = True
            await self._queue.put(None)  # 用 None 作为结束标记
    
    async def cleanup(self):
        """清理资源"""
        if not self._cleanup_done:
            self._cleanup_done = True
            # 清空队列
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.debug("StreamWriter resources cleaned up")
    
    async def error(self, error: str):
        """在流式输出中抛出错误"""
        if not self._error_occurred:
            self._error_occurred = True
            logger.error(f"Error in StreamWriter: {error}")
            error_chunk = AIMessageChunk(content=str(error))
            data = Chunk(
                metadata={},
                **error_chunk.model_dump()
            )
            await self._queue.put(data)
            await self.close()

    async def stream(self) -> AsyncIterator[str]:
        """流式输出数据"""
        try:
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
        except GeneratorExit:
            # 客户端断开连接，正常处理
            logger.debug("Client disconnected, closing stream")
            await self.close()
            await self.cleanup()
            raise
        except Exception as e:
            logger.error(f"Unexpected error in stream: {e}")
            await self.close()
            await self.cleanup()
            raise
        finally:
            # 确保发送结束标记
            try:
                if not self._error_occurred:
                    yield "data: [DONE]\n\n"
                else:
                    yield "data: [ERROR]\n\n"
            except GeneratorExit:
                # 客户端断开连接，不需要发送结束标记
                pass
            except Exception as e:
                logger.error(f"Error sending final marker: {e}")
            finally:
                await self.cleanup()

    def wrap_sse(self, data: Chunk) -> str:
        """将数据包装为 SSE 格式"""
        try:
            if isinstance(data, dict):
                pass
            else:
                data = data.model_dump()
        except Exception:
            try:
                data = json.loads(data)
            except Exception:
                logger.error(f"Invalid data: {data}, type: {type(data)}")
                raise ValueError(f"Invalid data: {data}, type: {type(data)}")
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"