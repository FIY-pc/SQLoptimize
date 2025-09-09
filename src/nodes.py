from typing import Dict, Any
import re
import sqlite3
import json

from .state import State
from .llm import get_llm
from .config import get_settings


def _ensure_history(state: State) -> None:
    if "history" not in state or state["history"] is None:
        state["history"] = []


def input_node(state: State) -> State:
    """输入节点：确保状态初始化并记录输入。"""
    _ensure_history(state)
    sql = state.get("input_sql", "").strip()
    if not sql:
        state["history"].append("[input] 未提供 input_sql")
    else:
        state["history"].append(f"[input] 接收到 SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")
    return state


def _extract_sql_from_text(text: str) -> str:
    """从 LLM 输出中提取 ```sql ... ``` 或 ``` ... ``` 代码块；若没有代码块，回退为原文。"""
    if not text:
        return ""
    # 优先匹配 ```sql ... ```
    m = re.search(r"```sql\s*\n(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    # 其次匹配通用 ``` ... ```
    m = re.search(r"```\s*\n(.*?)```", text, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def optimize_node(state: State) -> State:
    """优化节点：调用 LLM（qwen-plus）对 SQL 进行改写优化。"""
    _ensure_history(state)
    input_sql = state.get("input_sql", "").strip()
    if not input_sql:
        state["history"].append("[optimize] 缺少输入 SQL，跳过优化")
        return state

    prompt_system = (
        "你是一名资深数据库性能工程师。请在语义等价的前提下优化并规范化用户提供的 SQL：\n"
        "- 仅输出最终 SQL，使用 ```sql 代码块包裹；不要输出其它解释。"
    )
    prompt_user = f"原始 SQL：\n```sql\n{input_sql}\n```\n请给出优化后的 SQL。"

    # 组装消息，并注入自定义改写规则
    messages = [
        {"role": "system", "content": prompt_system},
        {"role": "user", "content": prompt_user},
    ]
    rewrite_rules = state.get("rewrite_rules")
    if rewrite_rules:
        try:
            rules_json = json.dumps(rewrite_rules, ensure_ascii=False, indent=2)
        except Exception:
            rules_json = str(rewrite_rules)
        # 记录注入规则的条数
        try:
            count = len(rewrite_rules.get("rules", [])) if isinstance(rewrite_rules, dict) and isinstance(rewrite_rules.get("rules", None), list) else 0
        except Exception:
            count = 0
        state["history"].append(f"[optimize] 将 {count} 条自定义规则注入 LLM")
        messages.append({
            "role": "user",
            "content": "以下为自定义改写规则（JSON），请严格参考但不要改变查询语义：\n```json\n"
                       + rules_json + "\n```"
        })

    llm = get_llm()
    content = llm.chat(messages)
    optimized_sql = _extract_sql_from_text(content)
    state["optimized_sql"] = optimized_sql
    state["history"].append("[optimize] 已生成优化 SQL")
    return state


def plan_check_node(state: State) -> State:
    """执行计划检查节点：
    - 若设置 DB_PATH 且可访问，使用 SQLite 的 EXPLAIN QUERY PLAN 获取计划反馈；
    - 否则使用 LLM 对 SQL 进行静态分析，给出潜在问题与建议。
    """
    _ensure_history(state)
    sql = (state.get("optimized_sql") or state.get("input_sql") or "").strip()
    if not sql:
        state["history"].append("[plan] 无 SQL 可检查")
        return state

    settings = get_settings()

    if settings.db_path:
        try:
            conn = sqlite3.connect(settings.db_path)
            cur = conn.cursor()
            # 只对第一条语句做 EXPLAIN QUERY PLAN
            first_stmt = sql.split(";")[0].strip()
            if first_stmt:
                cur.execute(f"EXPLAIN QUERY PLAN {first_stmt}")
                rows = cur.fetchall()
                plan_lines = [" | ".join(str(col) for col in row) for row in rows]
                feedback = "\n".join(plan_lines) if plan_lines else "(无计划结果)"
            else:
                feedback = "(无法解析 SQL 语句)"
            cur.close()
            conn.close()
            state["plan_feedback"] = f"SQLite 计划结果:\n{feedback}"
            state["history"].append("[plan] 已使用 SQLite EXPLAIN QUERY PLAN 生成反馈")
            return state
        except Exception as e:
            state["history"].append(f"[plan] SQLite 计划失败：{e}. 改用静态分析。")

    # 静态分析（LLM）
    prompt_system = (
        "你是数据库优化顾问。请对优化前后的SQL进行分析\n"
        "输出要点：用一句话简明扼要地分析改写过程"
    )
    
    input_sql = (state.get("input_sql") or "").strip()
    optimized_sql = (state.get("optimized_sql") or "").strip()

    if optimized_sql:
        prompt_user = (
            f"改写前SQL：\n```sql\n{input_sql}\n```\n"
            f"改写后SQL：\n```sql\n{optimized_sql}\n```\n"
            "请分析改写过程。"
        )
    else:
        prompt_user = (
            f"待分析 SQL：\n```sql\n{input_sql}\n```\n"
            "请给出静态分析与改进建议。"
        )

    # 后续把 prompt_user 传给 LLM
    try:
        llm = get_llm()
        content = llm.chat([
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user},
        ], temperature=0.1)
        state["plan_feedback"] = content.strip()
        state["history"].append("[plan] 已生成静态分析反馈")
    except Exception as e:
        state["plan_feedback"] = f"(静态分析不可用：{e})"
        state["history"].append("[plan] 静态分析失败")

    return state


def output_node(state: State) -> State:
    """输出节点：整理最终输出并记录。"""
    _ensure_history(state)
    has_opt = bool(state.get("optimized_sql"))
    has_plan = bool(state.get("plan_feedback"))
    state["history"].append(
        f"[output] 输出就绪：optimized_sql={'Y' if has_opt else 'N'}, plan_feedback={'Y' if has_plan else 'N'}"
    )
    return state