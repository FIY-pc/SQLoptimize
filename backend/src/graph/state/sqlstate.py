from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph.message import MessagesState
from src.llm import LLMClient
from src.utils.mysql_utils import MySQLUtils
class InputState(TypedDict, total=False):
    sql: str
    db_schema: Optional[str]
    database: Optional[str]
    max_iterations: int
    llm: LLMClient
    mysql_utils: MySQLUtils

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
    database: Optional[str]
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

    # 依赖
    llm: LLMClient
    mysql_utils: MySQLUtils

def build_initial_state(
    input_state: InputState
) -> SQLState:
    return {
        "messages": [],
        "sql": input_state.get("sql"),
        "db_schema": input_state.get("db_schema"),
        "database": input_state.get("database"),
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
        "max_iterations": input_state.get("max_iterations"),
        
        "llm": input_state.get("llm"),
        "mysql_utils": input_state.get("mysql_utils")
    }