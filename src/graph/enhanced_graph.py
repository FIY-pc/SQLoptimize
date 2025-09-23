"""增强的工作流图，支持多轮迭代优化和错误反馈"""

from typing import Callable

from langgraph.graph import StateGraph, START, END

from src.graph.state import State
from src.graph.enhanced_nodes import (
    enhanced_input_node,
    enhanced_optimize_node,
    syntax_check_node,
    quality_assessment_node,
    reflection_node
)
from src.graph.nodes import plan_check_node, verify_node, output_node


def should_retry_optimization(state: State) -> str:
    """决定是否需要重新优化"""
    assessment = state.get("quality_assessment", {})
    should_retry = assessment.get("should_retry", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = 3

    if should_retry and iteration_count < max_iterations:
        return "reflection"  # 进行反思后重新优化
    else:
        return "output"  # 结束优化流程


def should_continue_after_reflection(state: State) -> str:
    """反思后是否继续优化"""
    return "optimize"  # 总是返回优化节点进行下一轮


def build_enhanced_graph() -> Callable[[State], State]:
    """构建增强的工作流图"""
    workflow = StateGraph(State)

    # 注册所有节点
    workflow.add_node("input", enhanced_input_node)
    workflow.add_node("optimize", enhanced_optimize_node)
    workflow.add_node("plan", plan_check_node)
    workflow.add_node("syntax", syntax_check_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("quality", quality_assessment_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("output", output_node)

    # 线性流程
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "optimize")
    workflow.add_edge("optimize", "plan")
    workflow.add_edge("plan", "syntax")
    workflow.add_edge("syntax", "verify")
    workflow.add_edge("verify", "quality")

    # 条件分支：质量评估后决定是否重试
    workflow.add_conditional_edges(
        "quality",
        should_retry_optimization,
        {
            "reflection": "reflection",  # 需要重试，先反思
            "output": "output"           # 不需要重试，直接输出
        }
    )

    # 反思后继续优化
    workflow.add_conditional_edges(
        "reflection",
        should_continue_after_reflection,
        {
            "optimize": "optimize"  # 反思后重新优化
        }
    )

    # 结束
    workflow.add_edge("output", END)

    # 编译工作流
    app = workflow.compile()
    return app

def build_simple_enhanced_graph() -> Callable[[State], State]:
    """构建简化的增强工作流（不含多轮迭代）"""
    workflow = StateGraph(State)

    # 注册节点
    workflow.add_node("input", enhanced_input_node)
    workflow.add_node("optimize", enhanced_optimize_node)
    workflow.add_node("plan", plan_check_node)
    workflow.add_node("syntax", syntax_check_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("output", output_node)

    # 线性连接
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "optimize")
    workflow.add_edge("optimize", "plan")
    workflow.add_edge("plan", "syntax")
    workflow.add_edge("syntax", "verify")
    workflow.add_edge("verify", "output")
    workflow.add_edge("output", END)

    # 编译工作流
    app = workflow.compile()
    return app