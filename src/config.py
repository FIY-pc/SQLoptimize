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

    # 服务数据库连接配置
    service_db_url: str

    # OpenAI请求超时时间
    request_timeout: int = 60  # 秒

    # SQL等价性校验相关配置
    z3_lib_path: str = ""
    sqlsolver_jar_path: str = ""
    java_17_path: Optional[str] = ""
    
    # JWT认证相关配置
    jwt_secret_key: str = "INSECURE-DEFAULT-DO-NOT-USE"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # 测试用MySQL数据库连接配置
    mysql_host: Optional[str] = ""
    mysql_port: int = 3306
    mysql_user: Optional[str] = ""
    mysql_password: Optional[str] = ""
    mysql_database: Optional[str] = ""

    @staticmethod
    def from_env() -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        model = os.getenv("MODEL", "qwen-plus").strip()
        db_path = os.getenv("DB_PATH", "").strip() or "./data/app.db"
        service_db_url = os.getenv("SERVICE_DB_URL", "").strip()
        request_timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))

        # SQL等价性校验相关配置
        z3_lib_path = os.getenv("Z3_LIB_PATH", "").strip()
        sqlsolver_jar_path = os.getenv("SQLSOLVER_JAR_PATH", "").strip()
        java_17_path = os.getenv("JAVA_17_PATH", "").strip()    

        # JWT配置
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production").strip()
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
        jwt_access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        jwt_refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # MySQL连接配置
        mysql_host = os.getenv("MYSQL_HOST", "").strip() or None
        mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
        mysql_user = os.getenv("MYSQL_USER", "").strip() or None
        mysql_password = os.getenv("MYSQL_PASSWORD", "").strip() or None
        mysql_database = os.getenv("MYSQL_DATABASE", "").strip() or None

        return Settings(
            api_key=api_key,
            base_url=base_url,
            model=model,
            db_path=db_path,
            service_db_url=service_db_url,
            
            request_timeout=request_timeout,
            
            z3_lib_path=z3_lib_path,
            sqlsolver_jar_path=sqlsolver_jar_path,
            java_17_path=java_17_path,

            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=jwt_algorithm,
            jwt_access_token_expire_minutes=jwt_access_token_expire_minutes,
            jwt_refresh_token_expire_days=jwt_refresh_token_expire_days,
            
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_database=mysql_database,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()