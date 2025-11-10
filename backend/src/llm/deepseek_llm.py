from typing import List, Dict, Optional, TypedDict
from src.config import get_settings
from langchain.chat_models import init_chat_model


class DeepSeekLLMClient:

    api_type = "deepseek"

    def __init__(self, model: str, base_url: str, api_key: str, enable_thinking: bool = False) -> None:
        self._llm = init_chat_model(
            model=model,
            model_provider="deepseek",
            api_key=api_key,
            api_base=base_url,
        )

    @classmethod
    def create_from_settings(cls) -> "DeepSeekLLMClient":
        settings = get_settings()
        return cls(model=settings.model, base_url=settings.base_url, api_key=settings.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            resp = self._llm.invoke(
                messages,
                config={
                    "configurable": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                },
            )
        except Exception as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        content = resp.content if resp.content else ""
        return content or ""

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """异步调用 LLM"""
        try:
            resp = await self._llm.ainvoke(
                messages,
                config={
                    "configurable": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                },
            )
        except Exception as e:
            raise RuntimeError(f"调用 LLM 出错：{e}") from e
        content = resp.content if resp.content else ""
        return content or ""