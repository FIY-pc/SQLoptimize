from fastapi import FastAPI
from src.api.middleware import add_middleware
from src.api.routes.ai_router import ai_router
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="SQLoptimize API", version="0.1.0")

add_middleware(app)

app.include_router(ai_router)

# 健康检查
@app.get("/api/ping")
async def ping():
    return {"status": "ok"}