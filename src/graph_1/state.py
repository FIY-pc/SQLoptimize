from typing import TypedDict, Optional, Dict, Any, List


class SQLState(TypedDict, total=False):
    # 输入与上下文
    sql: str
    db_schema: Optional[str]
    history: List[str]

    # 查询计划、统计信息
    plan: str
    stats: Dict[str, Any]

    # LLM 优化输出
    optimized_sql: str

    # 等价性校验
    equivalence: bool

    # 成本估算
    cost_before: Optional[float]
    cost_after: Optional[float]

    # 重试控制
    iteration_count: int
    max_iterations: int


def build_initial_state(
    sql: str,
    db_schema: Optional[str] = None,
    max_iterations: int = 3
) -> SQLState:
    return {
        "sql": sql,
        "db_schema": db_schema,
        "history": [],
        "plan": "",
        "stats": {},
        "optimized_sql": "",
        "equivalence": False,
        "cost_before": None,
        "cost_after": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
    }