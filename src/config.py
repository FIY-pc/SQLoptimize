import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    db_path: Optional[str]
    request_timeout: int = 60  # 秒

    @staticmethod
    def from_env() -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        model = os.getenv("MODEL", "qwen-plus").strip()
        db_path = os.getenv("DB_PATH", "").strip() or None

        return Settings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            db_path=db_path,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()