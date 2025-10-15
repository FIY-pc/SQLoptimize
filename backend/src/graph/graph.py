from typing import Callable, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.graph.state import SQLState
from src.graph.tools.db_tools import run_explain, fetch_db_stats, run_explain_cost
from src.graph.tools.equiv import run_equivalence_checker
from src.graph.agent.llm_nodes import optimize_sql_node, final_report_node, generate_optimization_plans
import logging
from src.config import get_settings
from src.graph.dev.defalt_setting import default_setting_node

logger = logging.getLogger(__name__)

def input_node(state: SQLState) -> SQLState:
    logger.debug(f"call input_node")
    sql = (state.get("sql") or "").strip()
    # state.setdefault("history", []).append(
    #     f"[input] 接收到 SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}" if sql else "[input] 未提供 sql"
    # )
    return state


def get_query_plan_node(state: SQLState) -> SQLState:
    logger.debug(f"call get_query_plan_node")
    ok, plan_text = run_explain(state, state.get("sql", ""), database=None)
    state["plan"] = plan_text
    # state.setdefault("history", []).append(
    #     "[get_plan] 成功获取查询计划" if ok else f"[get_plan] 计划获取失败：{plan_text}"
    # )
    return state


def get_stats_node(state: SQLState) -> SQLState:
    logger.debug(f"call get_stats_node")
    stats = {}
    stats = fetch_db_stats(state, state.get("sql", ""), database=None)
    state["stats"] = stats
    # state.setdefault("history", []).append(
    #     "[get_stats] 成功获取统计信息" if stats.get("collection_success") else "[get_stats] 统计信息获取失败或部分失败"
    # )
    return state


def optimize_sql_node_wrapper(state: SQLState) -> SQLState:
    logger.debug(f"call optimize_sql_node_wrapper")
    state["iteration_count"] = int(state.get("iteration_count", 0)) + 1
    return optimize_sql_node(state) 


def equivalence_check_node(state: SQLState) -> SQLState:
    """检查当前方案的等价性"""
    logger.debug(f"call equivalence_check_node")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    
    if 0 <= current_index < len(plans):
        current_plan = plans[current_index]
        
        result = run_equivalence_checker(
            sql1=state.get("sql", ""),
            sql2=current_plan.get("optimized_sql", ""),
            db_schema=state.get("db_schema")
        )
        
        # hist = state.setdefault("history", [])
        
        if result.get("success"):
            is_equivalent = bool(result.get("equivalent", False))
            current_plan["equivalence"] = is_equivalent
            plans[current_index] = current_plan
            state["equivalence"] = is_equivalent
            # hist.append(f"[check_eq] 方案{current_index+1}工具校验：{'等价' if is_equivalent else '不等价'}")
        else:
            from src.graph.agent.llm_nodes import llm_equivalence_check  
            llm_res = llm_equivalence_check(
                state=state,
                sql1=state.get("sql", ""),
                sql2=current_plan.get("optimized_sql", ""),
                db_schema=state.get("db_schema")
            )
            is_equivalent = bool(llm_res.get("equivalent", False)) if llm_res.get("success") else False
            current_plan["equivalence"] = is_equivalent
            plans[current_index] = current_plan
            state["equivalence"] = is_equivalent
            # if llm_res.get("success"):
            #     hist.append(f"[check_eq] 方案{current_index+1}工具失败，LLM 校验：{'等价' if is_equivalent else '不等价'}")
            # else:
            #     hist.append(f"[check_eq] 方案{current_index+1}工具和 LLM 均校验失败：{llm_res.get('error', '未知错误')}")
            #     state["equivalence"] = False
    else:
        # state.setdefault("history", []).append(f"[check_eq] 无效的方案索引: {current_index}")
        state["equivalence"] = False
        
    return state


def get_costs_node(state: SQLState) -> SQLState:
    """获取当前方案的成本估算"""
    logger.debug(f"call get_costs_node")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    
    if not bool(state.get("equivalence", False)):
        # state.setdefault("history", []).append(f"[get_costs] 跳过方案{current_index+1}成本估算：未通过等价性验证")
        state["cost_before"] = None
        state["cost_after"] = None
        return state

    before = run_explain_cost(state, state.get("sql", ""), database=None)
    
    if 0 <= current_index < len(plans):
        current_plan = plans[current_index]
        after = run_explain_cost(state, current_plan.get("optimized_sql", ""), database=None)
        
        current_plan["cost"] = after
        plans[current_index] = current_plan
        
        state["cost_before"] = before
        state["cost_after"] = after
        
        # state.setdefault("history", []).append(
        #     f"[get_costs] 已获取方案{current_index+1}成本估算：改写前={before}, 改写后={after}"
        # )
    else:
        # state.setdefault("history", []).append(f"[get_costs] 无效的方案索引: {current_index}")
        state["cost_before"] = before
        state["cost_after"] = None
        
    return state


def next_plan_node(state: SQLState) -> SQLState:
    """切换到下一个优化方案"""
    logger.debug(f"call next_plan_node")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    
    next_index = current_index + 1
    
    if next_index < len(plans):
        state["current_plan_index"] = next_index
        state["optimized_sql"] = plans[next_index]["optimized_sql"]
        # state.setdefault("history", []).append(f"[next_plan] 切换到方案 {next_index+1}")
    else:
        # state.setdefault("history", []).append("[next_plan] 所有方案已处理完毕")
        pass
    
    return state


def should_process_next_plan(state: SQLState) -> str:
    """决定是否处理下一个方案"""
    logger.debug(f"call should_process_next_plan")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    
    if current_index + 1 < len(plans):
        return "next_plan"
    else:
        return "report"


def final_report_node_wrapper(state: SQLState) -> SQLState:
    logger.debug(f"call final_report_node_wrapper")
    return final_report_node(state)  # type: ignore


def should_retry_after_equivalence(state: SQLState) -> str:
    """
    - 等价 → 'get_costs'
    - 不等价且未达到最大迭代次数 → 'optimize_sql'
    - 不等价且达到最大迭代次数 → 'report'
    """
    eq = bool(state.get("equivalence", False))
    iter_count = int(state.get("iteration_count", 0))
    max_iters = int(state.get("max_iterations", 2))
    logger.debug(f"call should_retry_after_equivalence")
    if eq:
        # state.setdefault("history", []).append("[graph] 等价性满足，进入成本估算")
        return "get_costs"

    if iter_count < max_iters:
        # state.setdefault("history", []).append(f"[graph] 等价性不满足，准备第 {iter_count + 1} 次重试")
        return "optimize_sql"
    else:
        # state.setdefault("history", []).append("[graph] 等价性不满足，已达到最大重试次数，跳过成本估算，直接生成报告")
        return "report"


def build_sqlopt_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """构建SQL优化图"""
    graph = StateGraph(SQLState)

    settings = get_settings()

    # 如果在使用langsmith开发模式，则添加默认设置节点
    if settings.langsmith_dev_mode:
        graph.add_node("default_setting", default_setting_node)
    
    # 添加节点
    graph.add_node("input", input_node)
    graph.add_node("get_plan", get_query_plan_node)
    graph.add_node("get_stats", get_stats_node)
    graph.add_node("generate_plans", generate_optimization_plans)  
    graph.add_node("check_equivalence", equivalence_check_node)
    graph.add_node("get_costs", get_costs_node)
    graph.add_node("next_plan", next_plan_node)  
    graph.add_node("report", final_report_node_wrapper)
    
    # 设置边
    graph.set_entry_point("input")
    if settings.langsmith_dev_mode:
        graph.add_edge("input", "default_setting")
        graph.add_edge("default_setting", "get_plan")
    else:
        graph.add_edge("input", "get_plan")

    graph.add_edge("get_plan", "get_stats")
    graph.add_edge("get_stats", "generate_plans")  
    graph.add_edge("generate_plans", "check_equivalence")
    
    # 等价性检查后的路径
    graph.add_conditional_edges(
        "check_equivalence",
        lambda state: "get_costs" if state.get("equivalence", False) else "report",
        {
            "get_costs": "get_costs",
            "report": "report"
        }
    )
    
    # 成本估算后的路径
    graph.add_conditional_edges(
        "get_costs",
        should_process_next_plan,
        {
            "next_plan": "next_plan",
            "report": "report"
        }
    )
    
    # 处理下一个方案
    graph.add_edge("next_plan", "check_equivalence")
    
    # 设置结束点
    graph.add_edge("report", END)
    
    return graph.compile()