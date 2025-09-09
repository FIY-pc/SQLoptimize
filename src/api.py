from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .main import execute_pipeline

app = FastAPI(title="SQLoptimize API", version="0.1.0")

# 允许本地前端跨域调试（按需收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class OptimizeRequest(BaseModel):
    sql: str

class OptimizeResponse(BaseModel):
    input_sql: str
    optimized_sql: Optional[str] = None
    plan_feedback: Optional[str] = None
    history: List[str] = []

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    final_state = execute_pipeline(req.sql)
    return OptimizeResponse(
        input_sql=final_state.get("input_sql") or "",
        optimized_sql=final_state.get("optimized_sql"),
        plan_feedback=final_state.get("plan_feedback"),
        history=final_state.get("history") or [],
    )