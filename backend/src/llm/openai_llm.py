from typing import List, Dict, Optional, TypedDict
from langchain_openai import ChatOpenAI
from src.config import get_settings


class OpenAILLMClient:
    api_type = "openai"

    def __init__(self, model: str, base_url: str, api_key: str, enable_thinking: bool = False) -> None:
        self._client = ChatOpenAI(
            model=model,
            model_provider="openai",
            base_url=base_url,
            api_key=api_key,
        )

    @classmethod
    def create_from_settings(cls) -> "OpenAILLMClient":
        settings = get_settings()
        return cls(model=settings.model, base_url=settings.base_url, api_key=settings.api_key, enable_thinking=settings.enable_thinking)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        return self._client.invoke(messages, temperature=temperature, max_tokens=max_tokens, state=state)

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        return await self._client.ainvoke(messages, temperature=temperature, max_tokens=max_tokens, state=state)