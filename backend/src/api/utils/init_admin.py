from src.config import get_settings
from src.api.repository.user_repository import UserRepository
from src.schemas.repository.user import CreateUserReq
from src.api.utils import password_manager
from src.api.repository.database_connection_repository import DatabaseConnectionRepository
from src.schemas.repository.database import CreateDatabaseConnectionReq
from src.api.repository.model_connection_repository import ModelConnectionRepository
from src.schemas.repository.model import CreateModelConnectionReq
from src.api.repository.db_schema_repository import DbSchemaRepository
from src.schemas.repository.db_schema import CreateDbSchemaReq
import logging
from src.utils.path_utils import find_file_in_project
logger = logging.getLogger(__name__)



def init_admin_user():
    try:
        settings = get_settings()
        user_repository = UserRepository()
        
        # 检查管理员用户是否已存在
        if user_repository.exists_by_email(settings.admin_email):
            logger.info(f"Admin user already exists: {settings.admin_email}")
            return
        
        req = CreateUserReq(
            name=settings.admin_email,
            email=settings.admin_email,
            password=password_manager.hash_password(settings.admin_password)
        )
        try:
            user_repository.create(req)
            logger.info(f"Admin user created successfully: {settings.admin_email}")
        except Exception as e:
            logger.error(f"Admin user initialization failed: {e}")
            return

        # 获取用户ID
        user = user_repository.get_by_email(settings.admin_email)
        user_id = user.id

        # 初始化默认连接
        database_connection_repository = DatabaseConnectionRepository()
        if not database_connection_repository.get_by_name("default"):
            req = CreateDatabaseConnectionReq(
                database_name="default",
                database_uri=f"mysql://{settings.mysql_user}:{settings.mysql_password or ''}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}",
                database_type="mysql",
                database_description="default",
                user_id=user_id
            )
            database_connection_repository.create(req)
            logger.info("Default database connection created successfully")
        else:
            logger.info("Default database connection already exists")
        
        # 初始化默认模型
        model_connection_repository = ModelConnectionRepository()
        if not model_connection_repository.get_by_name(settings.model):
            req = CreateModelConnectionReq(
                model_name=settings.model,
                model=settings.model,
                base_url=settings.base_url,
                api_key=settings.api_key,
                user_id=user_id
            )
            model_connection_repository.create(req)
            logger.info(f"Default model connection created successfully: {settings.model}")
        else:
            logger.info(f"Default model connection already exists: {settings.model}")

        # 初始化默认schema
        db_schema_repository = DbSchemaRepository()
        if not db_schema_repository.get_by_name("default"):
            schema_path = find_file_in_project("schema.sql")
            
            if schema_path:
                with open(schema_path, mode="r", encoding="utf-8") as f:
                    schema_content = f.read()
                req = CreateDbSchemaReq(
                    schema_name="default",
                    schema_content=schema_content,
                    user_id=user_id
                )
                db_schema_repository.create(req)
                logger.info("Default schema created successfully")
            else:
                logger.warning("schema.sql file not found, skipping default schema creation")
        else:
            logger.info("Default schema already exists")
        logger.info("Admin user initialization completed successfully")
    except Exception as e:
        logger.error(f"Admin user initialization failed: {e}")
        raise
