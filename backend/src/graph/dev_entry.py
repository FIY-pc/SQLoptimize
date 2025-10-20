"""
LangGraph Studio 调试入口：
- 导出变量 `graph`，即 SQL 优化工作流的图应用
"""
from src.graph.graph import build_sqlopt_graph

# 构建图应用（StateGraph.compile 的返回值）
graph = build_sqlopt_graph()