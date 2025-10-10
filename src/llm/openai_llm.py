from typing import List, Dict, Optional
from openai import OpenAI, OpenAIError, AsyncOpenAI
from src.config import get_settings
from src.graph.state import SQLState as State
from src.llm.client import LLMClient


class OpenAILLMClient(LLMClient):
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
        
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        content = resp.choices[0].message.content if resp.choices else ""
        return content or ""

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[State] = None,
    ) -> str:
        """异步调用 LLM"""
        settings = get_settings()
        if not settings.api_key or settings.api_key == "EMPTY_KEY":
            raise RuntimeError("OPENAI_API_KEY 未设置，请先在环境变量或 .env 中配置。")

        try:
            resp = await self._client_async.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except OpenAIError as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e

        content = resp.choices[0].message.content if resp.choices else ""
        return content or ""
            