from fastapi import FastAPI
from src.api.middleware import add_middleware
from src.api.router import ai_router, auth_router, model_router, database_router, schema_router
from src.api.service_db import configure_service_db, migrate_service_db
from src.models.base import Base
from src.config import get_settings


settings = get_settings()

import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SQLoptimize API", 
    version="0.1.0",
    description="SQLoptimize API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    responses={404: {"description": "Not found"}},
)

add_middleware(app)

logger.info("Database setup start")
configure_service_db(settings.service_db_url)
migrate_service_db(Base)

logger.info("Database setup complete")

app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(model_router)
app.include_router(database_router)
app.include_router(schema_router)

# 健康检查
@app.get("/api/ping",summary="健康检查")
async def ping():
    return {"status": "ok"}