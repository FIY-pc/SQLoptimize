from typing import List, Dict, Optional, TypedDict, Literal
import abc
from typing import Type
from src.config import get_settings
from src.llm.aliyun_llm import AliyunLLMClient
from src.llm.openai_llm import OpenAILLMClient
from src.llm.deepseek_llm import DeepSeekLLMClient


LLM_API_TYPE = Literal["aliyun", "openai", "deepseek"]

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


class LLMClientFactory:
    
    llm_api_type_map: Dict[str, LLM_API_TYPE] = {
        "dashscope.aliyuncs.com": "aliyun",
        "openai.com": "openai",
        "api.deepseek.com": "deepseek",
    }

    llm_client_map: Dict[LLM_API_TYPE, Type[LLMClient]] = {
        "aliyun": AliyunLLMClient,
        "openai": OpenAILLMClient,
        "deepseek": DeepSeekLLMClient,
    }

    @staticmethod
    def extract_api_type(base_url: str) -> str:
        for key, value in LLMClientFactory.llm_api_type_map.items():
            if key in base_url:
                return value
        return "unknown"

    @staticmethod
    def create_llm_client(
        model: str, 
        base_url: str, 
        api_key: str, 
        enable_thinking: bool = False
    ) -> LLMClient:
        api_type = LLMClientFactory.extract_api_type(base_url)
        if api_type == "unknown":
            raise ValueError(f"Unknown API type: {base_url}")
        return LLMClientFactory.llm_client_map[api_type](model, base_url, api_key, enable_thinking)

    @staticmethod
    def create_from_settings() -> LLMClient:
        settings = get_settings()
        return LLMClientFactory.create_llm_client(
            model=settings.model,
            base_url=settings.base_url,
            api_key=settings.api_key,
            enable_thinking=settings.enable_thinking
        )

# 单例（惰性）获取
_llm_singleton: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_singleton
    if _llm_singleton is None:
        # 使用配置构建单例，避免无参初始化报错
        _llm_singleton = LLMClientFactory.create_from_settings()
    return _llm_singleton