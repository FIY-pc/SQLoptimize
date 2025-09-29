from typing import Dict, Any
import re

from src.llm import get_llm


def _extract_sql_from_text(text: str) -> str:
    """
    提取 LLM 输出中的 ```sql ... ``` 或 ``` ... ``` 代码块；若没有代码块，回退为原文。
    """
    if not text:
        return ""
    m = re.search(r"```sql\s*\n(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def optimize_sql_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM Node: OptimizeSQL
    输入：state["sql"], state["plan"], state["stats"]
    输出：state["optimized_sql"]
    """
    sql = (state.get("sql") or "").strip()
    plan = (state.get("plan") or "").strip()
    stats = state.get("stats") or {}

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深数据库性能优化专家。请在语义等价的前提下优化并规范化用户提供的 SQL：\n"
                "- 必须依据提供的查询计划（EXPLAIN）与数据库统计信息（如表行数、索引、列选择性等）进行优化决策；若统计信息缺失或不完整，请进行保守改写。\n"
                "- 优化目标：以降低 EXPLAIN JSON 中 query_block.cost_info.query_cost 为首要目标，且不改变结果集语义。\n"
                "- 优化策略：优先考虑索引使用与覆盖、谓词下推、调整连接顺序（基数驱动）、去除冗余子句/子查询、避免函数使索引失效、减少不必要的 DISTINCT/ORDER BY/FILESORT/TEMPORARY。\n"
                "- 输出要求：仅输出最终 SQL，使用 ```sql 代码块包裹；不要输出其它解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始 SQL：\n```sql\n{sql}\n```\n\n"
                f"查询计划：\n{plan}\n\n"
                f"统计信息（JSON）：\n```json\n{stats}\n```"
            ),
        },
    ]

    llm = get_llm()
    content = llm.chat(messages)
    optimized_sql = _extract_sql_from_text(content)
    state["optimized_sql"] = optimized_sql
    state.setdefault("history", []).append("[optimize_sql] 已生成候选改写 SQL")
    return state


def final_report_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM Node: FinalReport
    整合结果并输出概要报告到 state["final_report"]（字符串）
    """
    original_sql = state.get("sql", "")
    optimized_sql = state.get("optimized_sql", "")
    equivalence = state.get("equivalence", False)
    cost_before = state.get("cost_before")
    cost_after = state.get("cost_after")

    report_lines = [
        "=== SQL 优化报告 ===",
        f"原始 SQL:\n{original_sql}",
        f"\n优化后 SQL:\n{optimized_sql}",
        f"\n等价性校验结果: {'✔ 等价' if equivalence else '✘ 不等价'}",
    ]

    if cost_before is not None or cost_after is not None:
        report_lines.append("\n成本对比:")
        report_lines.append(f"- before: {cost_before if cost_before is not None else 'N/A'}")
        report_lines.append(f"- after:  {cost_after if cost_after is not None else 'N/A'}")
        if isinstance(cost_before, (int, float)) and isinstance(cost_after, (int, float)) and cost_before > 0:
            improvement = (cost_before - cost_after) / cost_before * 100.0
            report_lines.append(f"- improvement: {improvement:.2f}%")

    state["final_report"] = "\n".join(report_lines)
    state.setdefault("history", []).append("[final_report] 已生成优化报告")
    return state