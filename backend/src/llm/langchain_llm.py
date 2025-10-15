from typing import List, Dict, Optional, TypedDict
from src.config import get_settings
from src.llm.client import LLMClient
from langchain.chat_models import init_chat_model


class LangchainLLMClient(LLMClient):
    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        
        self._llm = init_chat_model(
            model=model,
            api_key=api_key or "EMPTY_KEY",
            base_url=base_url,
            model_provider="openai",
        )
    @classmethod
    def create_from_settings(cls) -> "LangchainLLMClient":
        settings = get_settings()
        return cls(model=settings.model, base_url=settings.base_url, api_key=settings.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        settings = get_settings()
        if not settings.api_key or settings.api_key == "EMPTY_KEY":
            raise RuntimeError("OPENAI_API_KEY 未设置，请先在环境变量或 .env 中配置。")
        
        self._llm.bind(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            resp = self._llm.invoke(messages)
        except Exception as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        content = resp.content if resp.content else ""
        return content or ""

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        """异步调用 LLM"""
        settings = get_settings()
        if not settings.api_key or settings.api_key == "EMPTY_KEY":
            raise RuntimeError("OPENAI_API_KEY 未设置，请先在环境变量或 .env 中配置。")

        self._llm.bind(
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            resp = await self._llm.ainvoke(messages)
        except Exception as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        content = resp.content if resp.content else ""
        return content or ""