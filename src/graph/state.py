from typing import TypedDict, Optional, Dict, Any, List, Annotated
from langgraph.graph.message import add_messages
from langgraph.graph.message import MessagesState


class OptimizationPlan(TypedDict, total=False):
    plan_id: str
    description: str
    optimized_sql: str
    reasoning: str
    equivalence: bool
    cost: Optional[float]


class SQLState(MessagesState, total=False):
    # 输入与上下文
    sql: str
    db_schema: Optional[str]
    # history: List[str]

    # 查询计划、统计信息
    plan: str
    stats: Dict[str, Any]

    # 多方案优化
    optimization_plans: List[OptimizationPlan]
    current_plan_index: int
    
    optimized_sql: str
    rewrite_explanation: str
    equivalence: bool
    cost_before: Optional[float]
    cost_after: Optional[float]

    # 重试控制
    iteration_count: int
    max_iterations: int
    
    # 最终报告
    final_report: str


def build_initial_state(
    sql: str,
    db_schema: Optional[str] = None,
    max_iterations: int = 3
) -> SQLState:
    return {
        "messages": [],
        "sql": sql,
        "db_schema": db_schema,
        # "history": [],
        "plan": "",
        "stats": {},
        "optimization_plans": [],
        "current_plan_index": -1,
        "optimized_sql": "",
        "equivalence": False,
        "cost_before": None,
        "cost_after": None,
        "iteration_count": 0,
        "max_iterations": max_iterations,
    }