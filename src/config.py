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
    z3_jar_path: str = "./src/sql_equality/lib/sqlsolver-v1.1.0.jar"
    
    # JWT认证相关配置
    jwt_secret_key: str = "INSECURE-DEFAULT-DO-NOT-USE"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @staticmethod
    def from_env() -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        model = os.getenv("MODEL", "qwen-plus").strip()
        db_path = os.getenv("DB_PATH", "").strip() or "./data/app.db"
        z3_jar_path = os.getenv("Z3_JAR_PATH", "").strip()
        
        # JWT配置
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production").strip()
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
        jwt_access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        jwt_refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        return Settings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            db_path=db_path,
            z3_jar_path=z3_jar_path,
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=jwt_algorithm,
            jwt_access_token_expire_minutes=jwt_access_token_expire_minutes,
            jwt_refresh_token_expire_days=jwt_refresh_token_expire_days,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()