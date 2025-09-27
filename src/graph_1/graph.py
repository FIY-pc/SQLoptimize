from typing import Callable

from langgraph.graph import StateGraph, START, END

from src.graph_1.state import SQLState
from src.graph_1.tools.db_tools import run_explain, fetch_db_stats, run_explain_cost
from src.graph_1.tools.equiv import run_equivalence_checker
from src.graph_1.agent.llm_nodes import optimize_sql_node, final_report_node


def input_node(state: SQLState) -> SQLState:
    sql = (state.get("sql") or "").strip()
    state.setdefault("history", []).append(
        f"[input] 接收到 SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}" if sql else "[input] 未提供 sql"
    )
    return state


def get_query_plan_node(state: SQLState) -> SQLState:
    ok, plan_text = run_explain(state.get("sql", ""), database=None)
    state["plan"] = plan_text
    state.setdefault("history", []).append(
        "[get_plan] 成功获取查询计划" if ok else f"[get_plan] 计划获取失败：{plan_text}"
    )
    return state


def get_stats_node(state: SQLState) -> SQLState:
    stats = fetch_db_stats(state.get("sql", ""), database=None)
    state["stats"] = stats
    state.setdefault("history", []).append(
        "[get_stats] 成功获取统计信息" if stats.get("collection_success") else "[get_stats] 统计信息获取失败或部分失败"
    )
    return state


def optimize_sql_node_wrapper(state: SQLState) -> SQLState:
    state["iteration_count"] = int(state.get("iteration_count", 0)) + 1
    return optimize_sql_node(state) 


def equivalence_check_node(state: SQLState) -> SQLState:
    result = run_equivalence_checker(
        sql1=state.get("sql", ""),
        sql2=state.get("optimized_sql", ""),
        db_schema=state.get("db_schema")
    )
    state["equivalence"] = bool(result.get("equivalent", False))
    hist = state.setdefault("history", [])
    if result.get("success"):
        hist.append(f"[check_eq] 等价性验证完成：{'等价' if state['equivalence'] else '不等价'}")
    else:
        hist.append(f"[check_eq] 验证失败：{result.get('error', '未知错误')}")
        state["equivalence"] = False
    return state


def get_costs_node(state: SQLState) -> SQLState:
    # 防御性判断：仅当等价性通过时才进行成本估算
    if not bool(state.get("equivalence", False)):
        state.setdefault("history", []).append("[get_costs] 跳过成本估算：未通过等价性验证")
        state["cost_before"] = None
        state["cost_after"] = None
        return state

    before = run_explain_cost(state.get("sql", ""), database=None)
    after = run_explain_cost(state.get("optimized_sql", ""), database=None)
    state["cost_before"] = before
    state["cost_after"] = after
    state.setdefault("history", []).append(f"[get_costs] 已获取成本估算：改写前={before}, 改写后={after}")
    return state


def final_report_node_wrapper(state: SQLState) -> SQLState:
    return final_report_node(state)  # type: ignore


def should_retry_after_equivalence(state: SQLState) -> str:
    """
    强制门控：
    - 等价 → 'get_costs'
    - 不等价且未达到最大迭代次数 → 'optimize_sql'
    - 不等价且达到最大迭代次数 → 'report'
    """
    eq = bool(state.get("equivalence", False))
    iter_count = int(state.get("iteration_count", 0))
    max_iters = int(state.get("max_iterations", 2))

    if eq:
        state.setdefault("history", []).append("[graph] 等价性满足，进入成本估算")
        return "get_costs"

    # 不等价
    if iter_count < max_iters:
        state.setdefault("history", []).append(f"[graph] 等价性不满足，准备第 {iter_count + 1} 次重试")
        return "optimize_sql"
    else:
        state.setdefault("history", []).append("[graph] 等价性不满足，已达到最大重试次数，跳过成本估算，直接生成报告")
        return "report"


def build_sqlopt_graph() -> Callable[[SQLState], SQLState]:
    workflow = StateGraph(SQLState)

    # 注册节点
    workflow.add_node("input", input_node)
    workflow.add_node("get_plan", get_query_plan_node)
    workflow.add_node("get_stats", get_stats_node)
    workflow.add_node("optimize_sql", optimize_sql_node_wrapper)
    workflow.add_node("check_eq", equivalence_check_node)
    workflow.add_node("get_costs", get_costs_node)
    workflow.add_node("report", final_report_node_wrapper)

    # 线性连接
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "get_plan")
    workflow.add_edge("get_plan", "get_stats")
    workflow.add_edge("get_stats", "optimize_sql")
    workflow.add_edge("optimize_sql", "check_eq")

    # 条件分支：强制门控（仅等价时进入成本估算；否则重试或直接报告）
    workflow.add_conditional_edges(
        "check_eq",
        should_retry_after_equivalence,
        {
            "optimize_sql": "optimize_sql",
            "get_costs": "get_costs",
            "report": "report",
        }
    )

    workflow.add_edge("get_costs", "report")
    workflow.add_edge("report", END)

    app = workflow.compile()
    return app