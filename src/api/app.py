from fastapi import FastAPI
from src.api.middleware import add_middleware
from src.api.router import ai_router, auth_router
from src.api.database import ensure_db_setup, create_tables
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
ensure_db_setup()
create_tables()
logger.info("Database setup complete")

app.include_router(ai_router)
app.include_router(auth_router)

# 健康检查
@app.get("/api/ping")
async def ping():
    return {"status": "ok"}