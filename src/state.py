from typing import TypedDict, List, Optional, Dict, Any, Callable
from src.stream.stream_writer import StreamWriter

class State(TypedDict, total=False):
    # 输入 SQL（用户传入）
    input_sql: str

    # 数据库 schema
    db_schema: Optional[str]

    # z3 验证结果
    z3_result: Optional[List[str]]

    # LLM 生成的优化后 SQL
    optimized_sql: Optional[str]

    # 执行计划或静态分析反馈（字符串）
    plan_feedback: Optional[str]

    # 历史轨迹（每个节点可追加日志，便于调试与追溯）
    history: List[str]

    # 自定义改写规则（直接传给 LLM），顶层建议是一个字典
    rewrite_rules: Optional[dict]

    # 流式输出 writer
    stream_writer: Optional[StreamWriter]