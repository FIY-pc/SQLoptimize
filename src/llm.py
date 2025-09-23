from typing import List, Dict, Optional
from openai import OpenAI, OpenAIError, AsyncOpenAI
from .config import get_settings
from src.graph.state import State
from .schemas.stream_chunk import Chunk, LLMChunk
from src.utils import get_unix_timestamp


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        
        self._client = OpenAI(
            api_key=settings.api_key or "EMPTY_KEY",
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )
        
        self._client_async = AsyncOpenAI(
            api_key=settings.api_key or "EMPTY_KEY",
            base_url=settings.base_url,
            timeout=settings.request_timeout,
        )
        
        self._model = settings.model

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[State] = None,
    ) -> str:
        settings = get_settings()
        if not settings.api_key or settings.api_key == "EMPTY_KEY":
            raise RuntimeError("OPENAI_API_KEY 未设置，请先在环境变量或 .env 中配置。")
        
        stream_writer = state.get("stream_writer") if state is not None else None
        
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True if stream_writer else False,
            )
        except OpenAIError as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        if stream_writer:
            content = ""
            for chunk in resp:
                delta = chunk.choices[0].delta.content if chunk.choices else ""
                if delta:
                    content += delta
                    stream_writer.write(self._wrap_llm_chunk(chunk))
            return content or ""
        else:
            content = resp.choices[0].message.content if resp.choices else ""
            return content or ""

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[State] = None,
    ) -> str:
        settings = get_settings()
        if not settings.api_key or settings.api_key == "EMPTY_KEY":
            raise RuntimeError("OPENAI_API_KEY 未设置，请先在环境变量或 .env 中配置。")

        stream_writer = state.get("stream_writer") if state is not None else None

        try:
            resp = self._client_async.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True if stream_writer else False,
            )
        except OpenAIError as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        if stream_writer:
            content = ""
            for chunk in resp:
                delta = chunk.choices[0].delta.content if chunk.choices else ""
                if delta:
                    content += delta
                    await stream_writer.write(self._wrap_llm_chunk(chunk))
            return content or ""
        else:
            content = resp.choices[0].message.content if resp.choices else ""
            return content or ""
            
    def _wrap_llm_chunk(self, chunk: dict) -> Chunk:
        llm_chunk = LLMChunk(
            content=chunk.choices[0].delta.content if chunk.choices else "",
        )
        return Chunk(
            type="llm_chunk",
            data=llm_chunk,
            timestamp=get_unix_timestamp()
        )

# 单例（惰性）获取
_llm_singleton: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_singleton
    if _llm_singleton is None:
        _llm_singleton = LLMClient()
    return _llm_singleton