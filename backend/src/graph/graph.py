from typing import Callable, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.graph.state import SQLState
from src.graph.tools.db_tools import run_explain, fetch_db_stats, run_explain_cost
from src.graph.tools.equiv import run_equivalence_checker
from src.graph.agent.llm_nodes import final_report_node, generate_optimization_plans, fix_sql_with_explain_error, fix_sql_with_equivalence_reason
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


async def get_query_plan_node(state: SQLState) -> SQLState:
    logger.debug(f"call get_query_plan_node")
    database = state.get("database")
    ok, plan_text = await run_explain(state, state.get("sql", ""), database=database)
    state["plan"] = plan_text
    return state


async def get_stats_node(state: SQLState) -> SQLState:
    logger.debug(f"call get_stats_node")
    database = state.get("database")
    stats = await fetch_db_stats(state, state.get("sql", ""), database=database)
    state["stats"] = stats
    return state



async def equivalence_check_node(state: SQLState) -> SQLState:
    """检查当前方案的等价性"""
    logger.debug(f"call equivalence_check_node")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    
    if 0 <= current_index < len(plans):
        current_plan = plans[current_index]
        
        result = await run_equivalence_checker(
            sql1=state.get("sql", ""),
            sql2=current_plan.get("optimized_sql", ""),
            db_schema=state.get("db_schema")
        )
        
        if result.get("success"):
            is_equivalent = bool(result.get("equivalent", False))
            current_plan["equivalence"] = is_equivalent
            # 记录工具返回的原因（details），仅在不等价时保存
            if not is_equivalent:
                reason = str(result.get("details") or "")
                current_plan["equivalence_reason"] = reason
                state["equivalence_reason"] = reason
                state["need_fix_equivalence"] = True
            else:
                current_plan["equivalence_reason"] = ""
                state["equivalence_reason"] = ""
                state["need_fix_equivalence"] = False
            plans[current_index] = current_plan
            state["equivalence"] = is_equivalent
        else:
            from src.graph.agent.llm_nodes import llm_equivalence_check  
            llm_res = await llm_equivalence_check(
                state=state,
                sql1=state.get("sql", ""),
                sql2=current_plan.get("optimized_sql", ""),
                db_schema=state.get("db_schema")
            )
            is_equivalent = bool(llm_res.get("equivalent", False)) if llm_res.get("success") else False
            current_plan["equivalence"] = is_equivalent
            # 保存 LLM 的不等价原因
            reason = str(llm_res.get("reason") or "")
            current_plan["equivalence_reason"] = "" if is_equivalent else reason
            state["equivalence_reason"] = "" if is_equivalent else reason
            state["need_fix_equivalence"] = not is_equivalent
            plans[current_index] = current_plan
            state["equivalence"] = is_equivalent
    else:
        state["equivalence"] = False
        
    return state

def route_after_equivalence(state: SQLState) -> str:
    """等价性检查后的路由：等价→get_costs；不等价→fix_equivalence/next_plan/report"""
    logger.debug(f"call route_after_equivalence")
    if state.get("equivalence", False):
        return "get_costs"

    current_index = int(state.get("current_plan_index", 0))
    plans = state.get("optimization_plans", [])
    max_iters = int(state.get("max_iterations", 2) or 2)

    # 当前方案的已尝试次数
    attempts = 0
    if 0 <= current_index < len(plans):
        attempts = int(plans[current_index].get("eq_fix_attempts", 0))

    # 未达上限 → 继续修复
    if attempts < max_iters:
        return "fix_equivalence"

    # 达到上限 → 若有下一方案则切换，否则报告
    if current_index + 1 < len(plans):
        return "next_plan"
    return "report"


async def get_costs_node(state: SQLState) -> SQLState:
    """获取当前方案的成本估算"""
    logger.debug(f"call get_costs_node")
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])

    if not bool(state.get("equivalence", False)):
        state["cost_before"] = None
        state["cost_after"] = None
        return state

    database = state.get("database")

    before = await run_explain_cost(state, state.get("sql", ""), database=database)

    if 0 <= current_index < len(plans):
        current_plan = plans[current_index]

        # 同步最新修复的 SQL（若与方案中的不一致）
        after_sql = (current_plan.get("optimized_sql") or "").strip()
        fixed_candidate = (state.get("optimized_sql") or "").strip()
        if fixed_candidate and fixed_candidate != after_sql:
            after_sql = fixed_candidate
            current_plan["optimized_sql"] = fixed_candidate
            plans[current_index] = current_plan
            state["optimization_plans"] = plans

        after = await run_explain_cost(state, after_sql, database=database)

        if before is None or after is None:
            err = None
            mysql_utils = state.get("mysql_utils")
            try:
                if after is None and mysql_utils:
                    r2 = await mysql_utils.get_mysql_explain_plan(current_plan.get("optimized_sql", ""), database=database)
                    if not r2.get("success"):
                        err = r2.get("error")
                elif before is None and mysql_utils:
                    r1 = await mysql_utils.get_mysql_explain_plan(state.get("sql", ""), database=database)
                    if not r1.get("success"):
                        err = r1.get("error")
            except Exception as e:
                err = str(e)

            if err:
                state["explain_error"] = err
                state["need_fix_sql"] = True
                current_plan["cost"] = None
                plans[current_index] = current_plan
                state["optimization_plans"] = plans
                state["cost_before"] = before
                state["cost_after"] = None
                return state

        current_plan["cost"] = after
        plans[current_index] = current_plan
        state["optimization_plans"] = plans

        state["cost_before"] = before
        state["cost_after"] = after
    else:
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
        # 清理等价性修复标记，避免遗留状态影响新方案
        state["equivalence_reason"] = ""
        state["need_fix_equivalence"] = False
        # state.setdefault("history", []).append(f"[next_plan] 切换到方案 {next_index+1}")
    else:
        # state.setdefault("history", []).append("[next_plan] 所有方案已处理完毕")
        pass
    
    return state


def should_process_next_plan(state: SQLState) -> str:
    """决定是否处理下一个方案"""
    logger.debug(f"call should_process_next_plan")
    if bool(state.get("need_fix_sql", False)) or bool(state.get("explain_error")):
        return "fix_sql"
    current_index = state.get("current_plan_index", 0)
    plans = state.get("optimization_plans", [])
    if current_index + 1 < len(plans):
        return "next_plan"
    else:
        return "report"


async def final_report_node_wrapper(state: SQLState) -> SQLState:
    logger.debug(f"call final_report_node_wrapper")
    return await final_report_node(state)  # type: ignore


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
    graph.add_node("fix_sql", fix_sql_with_explain_error)
    # 新增：等价性修复节点
    graph.add_node("fix_equivalence", fix_sql_with_equivalence_reason)
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
    
    # 等价性检查后的路径（修改：非等价进入修复）
    graph.add_conditional_edges(
        "check_equivalence",
        route_after_equivalence,
        {
            "get_costs": "get_costs",
            "fix_equivalence": "fix_equivalence",
            "next_plan": "next_plan",
            "report": "report"
        }
    )

    # 修复后回到等价性校验
    graph.add_edge("fix_equivalence", "check_equivalence")

    # 成本估算后的路径（已有）
    graph.add_conditional_edges(
        "get_costs",
        should_process_next_plan,
        {
            "next_plan": "next_plan",
            "fix_sql": "fix_sql",
            "report": "report"
        }
    )
    graph.add_edge("fix_sql", "get_costs")
    
    # 处理下一个方案
    graph.add_edge("next_plan", "check_equivalence")
    
    # 设置结束点
    graph.add_edge("report", END)
    
    return graph.compile()