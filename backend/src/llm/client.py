from typing import List, Dict, Optional, TypedDict
import abc


class LLMClient(abc.ABC):
    """
    LLM客户端抽象基类
    """

    @abc.abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        state: Optional[TypedDict] = None,
    ) -> str:
        raise NotImplementedError


# 单例（惰性）获取
_llm_singleton: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_singleton
    if _llm_singleton is None:
        from .langchain_llm import LangchainLLMClient
        _llm_singleton = LangchainLLMClient()
    return _llm_singleton