from typing import List, Dict, Optional, TypedDict
from openai import OpenAI, OpenAIError, AsyncOpenAI
from src.config import get_settings
from src.llm.client import LLMClient


class OpenAILLMClient(LLMClient):
    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        self._model = model
        self._base_url = base_url
        self._api_key = api_key

        settings = get_settings()
        
        self._client = OpenAI(
            api_key=self._api_key or "EMPTY_KEY",
            base_url=self._base_url,
            timeout=settings.request_timeout,
        )
        
        self._client_async = AsyncOpenAI(
            api_key=self._api_key or "EMPTY_KEY",
            base_url=self._base_url,
            timeout=settings.request_timeout,
        )
        

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        if not self._api_key or self._api_key == "EMPTY_KEY":
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
        state: Optional[TypedDict] = None,
    ) -> str:
        """异步调用 LLM"""
        if not self._api_key or self._api_key == "EMPTY_KEY":
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
            