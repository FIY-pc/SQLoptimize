from typing import Callable

from langgraph.graph import StateGraph, START, END

from .state import State
from .nodes_async import input_node_async, optimize_node_async, plan_check_node_async, output_node_async


def build_async_graph() -> Callable[[State], State]:
    workflow = StateGraph(State)

    # 注册节点
    workflow.add_node("input", input_node_async)
    workflow.add_node("optimize", optimize_node_async)
    workflow.add_node("plan", plan_check_node_async)
    workflow.add_node("output", output_node_async)

    # 连接边
    workflow.add_edge(START, "input")
    workflow.add_edge("input", "optimize")
    workflow.add_edge("optimize", "plan")
    workflow.add_edge("plan", "output")
    workflow.add_edge("output", END)

    # 编译得到可调用对象（同步）
    app = workflow.compile()
    return app