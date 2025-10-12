from typing import Dict, Any, Optional, Tuple
import json

from src.config import get_settings
from src.graph.state import SQLState


def run_explain(state: SQLState ,sql: str, database: Optional[str] = None) -> Tuple[bool, str]:
    """
    获取查询计划（优先 MySQL，回退 SQLite）。
    返回 (success, plan_text)
    """
    settings = get_settings()

    # Try MySQL first
    mysql_utils = state.get("mysql_utils")
    
    if mysql_utils:
        try:
            conn_test = mysql_utils.test_mysql_connection()
            if not conn_test["success"]:
                return False, f"MySQL连接失败: {conn_test.get('error', '未知错误')}"

            plan_result = mysql_utils.get_mysql_explain_plan(sql, database or settings.mysql_database)
            if plan_result["success"]:
                parts = []
                if plan_result.get("explain_json"):
                    parts.append("MySQL EXPLAIN (JSON):")
                    ej = plan_result["explain_json"]
                    if isinstance(ej, str):
                        try:
                            ej = json.loads(ej)
                        except Exception:
                            # 保持原样（字符串），避免中断
                            pass
                    parts.append(json.dumps(ej, ensure_ascii=False, indent=2))
                if plan_result.get("explain_traditional"):
                    parts.append("\nMySQL EXPLAIN (传统格式):")
                    for row in plan_result["explain_traditional"]:
                        if isinstance(row, dict):
                            parts.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
                        else:
                            parts.append(" | ".join(str(col) for col in row))
                return True, "\n".join(parts)
            else:
                return False, f"MySQL EXPLAIN失败: {plan_result.get('error', '未知错误')}"
        except Exception as e:
            return False, f"MySQL EXPLAIN异常: {e}"

    # Fallback SQLite
    try:
        conn = state.get("fallback_sqlite")
        if not conn:
            return False, "未配置 db_path，无法使用 SQLite EXPLAIN QUERY PLAN"
        cur = conn.cursor()
        first_stmt = sql.split(";")[0].strip()
        if not first_stmt:
            return False, "无法解析 SQL 语句（空或无有效语句）"
        cur.execute(f"EXPLAIN QUERY PLAN {first_stmt}")
        rows = cur.fetchall()
        plan_lines = [" | ".join(str(col) for col in row) for row in rows]
        cur.close()
        conn.close()
        return True, "SQLite EXPLAIN QUERY PLAN:\n" + ("\n".join(plan_lines) if plan_lines else "(无计划结果)")
    except Exception as e:
        return False, f"SQLite EXPLAIN失败: {e}"


def run_explain_cost(state: SQLState, sql: str, database: Optional[str] = None) -> Optional[float]:
    """
    提取 EXPLAIN (FORMAT JSON) 的成本估计（若可用）。
    当前使用 MySQL 的 JSON EXPLAIN（如果包含 cost_info 则返回其中的总成本或近似）。
    若不可用，则返回 None。
    """

    mysql_utils = state.get("mysql_utils")
    settings = get_settings()
    if mysql_utils:
        try:
            plan_result = mysql_utils.get_mysql_explain_plan(sql, database or settings.mysql_database)
            if plan_result["success"] and plan_result.get("explain_json"):
                explain_json = plan_result["explain_json"]

                # EXPLAIN FORMAT=JSON 常常返回字符串，这里先解析为字典
                if isinstance(explain_json, str):
                    try:
                        explain_json = json.loads(explain_json)
                    except Exception:
                        return None

                # 安全地转换为 float
                def to_float_safe(val) -> Optional[float]:
                    if isinstance(val, (int, float)):
                        return float(val)
                    if isinstance(val, str):
                        try:
                            return float(val)
                        except ValueError:
                            return None
                    return None

                # 优先尝试顶层 query_block.cost_info.query_cost
                try:
                    qb = explain_json.get("query_block", {})
                    ci = qb.get("cost_info", {})
                    qc = to_float_safe(ci.get("query_cost"))
                    if qc is not None:
                        return qc
                except Exception:
                    pass

                # 递归查找任意位置的 cost_info，并提取 query_cost（或兼容字段）
                def find_query_cost(obj) -> Optional[float]:
                    if isinstance(obj, dict):
                        ci = obj.get("cost_info")
                        if isinstance(ci, dict):
                            # 以 query_cost 为主；其他字段仅作兼容备用
                            primary = to_float_safe(ci.get("query_cost"))
                            if primary is not None:
                                return primary
                            for key in ("estimation_cost", "cost", "query_cost_estimate", "sort_cost", "read_cost", "eval_cost", "prefix_cost"):
                                val = to_float_safe(ci.get(key))
                                # 若确实没有 query_cost，则返回第一个可解析的成本字段
                                if val is not None:
                                    return val
                        # 遍历子节点
                        for v in obj.values():
                            res = find_query_cost(v)
                            if res is not None:
                                return res
                    elif isinstance(obj, list):
                        for item in obj:
                            res = find_query_cost(item)
                            if res is not None:
                                return res
                    return None

                return find_query_cost(explain_json)
            return None
        except Exception:
            return None
    # SQLite 不提供对象化成本（仅返回 None 作为占位）
    return None


def fetch_db_stats(state: SQLState, sql: str, database: Optional[str] = None) -> Dict[str, Any]:
    """
    获取数据库统计信息
    返回包含表信息、列、索引、以及采集过程中的错误。
    """
    stats: Dict[str, Any] = {
        "collection_success": False,
        "collection_errors": [],
        "table_statistics": {},
    }
    mysql_utils = state.get("mysql_utils")
    settings = get_settings()
    if mysql_utils:
        try:
            mysql_utils = MySQLUtils.create_from_settings()
            # 从 SQL/EXPLAIN + LLM 中解析表名,并收集这些表的统计信息

            import re
            import json

            def ask_llm_for_tables(sql_text: str, explain_json_text: Optional[str]) -> set[str]:
                try:
                    from src.llm.client import get_llm
                    llm = get_llm()
                except Exception as e:
                    stats["collection_errors"].append(f"LLM 初始化失败，跳过 LLM 表名提取：{e}")
                    return set()

                TPCH_TABLES = {
                    "nation", "region", "part", "supplier", "partsupp",
                    "customer", "orders", "lineitem",
                }
                TPCDS_TABLES = {
                    "call_center", "catalog_page", "catalog_returns", "catalog_sales",
                    "customer", "customer_address", "customer_demographics", "date_dim",
                    "dbgen_version", "household_demographics", "income_band", "inventory",
                    "item", "promotion", "reason", "ship_mode", "store", "store_returns",
                    "store_sales", "time_dim", "warehouse", "web_page", "web_returns",
                    "web_sales", "web_site",
                }
                whitelist = TPCH_TABLES | TPCDS_TABLES

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "你是一个SQL分析助手。给定一条SQL查询以及可选的MySQL EXPLAIN FORMAT=JSON执行计划，"
                            "请只提取基础表名（即FROM/JOIN的真实来源表）。"
                            "不要包含CTE名称、别名、子查询/派生表或视图。"
                            "输出必须是逗号分隔的小写列表。"
                            "只返回存在于如下白名单（TPCH/TPCDS）的名称；不在白名单的名称请忽略。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"SQL：\n{sql_text}\n\n"
                            f"EXPLAIN JSON：\n{explain_json_text or '(无)'}\n\n"
                            "TPCH白名单：\n"
                            + ", ".join(sorted(TPCH_TABLES))
                            + "\nTPCDS白名单：\n"
                            + ", ".join(sorted(TPCDS_TABLES))
                            + "\n请只输出逗号分隔的小写表名列表。"
                        ),
                    },
                ]

                try:
                    content = llm.chat(messages=messages, temperature=0.0, max_tokens=512)
                except Exception as e:
                    stats["collection_errors"].append(f"LLM 表名提取调用失败：{e}")
                    return set()

                raw = content.strip()
                if not raw:
                    return set()
                candidates = set()
                for token in re.split(r"[,\s]+", raw):
                    t = token.strip().strip('`"')
                    if not t:
                        continue
                    if "." in t:
                        t = t.split(".")[-1]
                    t = t.lower()
                    if t in whitelist:
                        candidates.add(t)
                return candidates

            def _extract_tables_from_explain_json(plan_text: str) -> set[str]:
                try:
                    obj = json.loads(plan_text)
                except Exception:
                    return set()

                names: set[str] = set()

                def walk(node):
                    if isinstance(node, dict):
                        if "table" in node and isinstance(node["table"], dict):
                            tname = node["table"].get("table_name") or node["table"].get("name")
                            if isinstance(tname, str):
                                names.add(tname)
                        if "table_name" in node and isinstance(node["table_name"], str):
                            names.add(node["table_name"])
                        for v in node.values():
                            walk(v)
                    elif isinstance(node, list):
                        for item in node:
                            walk(item)

                walk(obj)

                def is_derived(s: str) -> bool:
                    s = s.strip()
                    return (s.startswith("<") and s.endswith(">")) or s.lower().startswith("derived_") or s.lower().startswith("subquery_")

                return {n for n in names if not is_derived(n)}

            def _parse_table_names(sql_text: str) -> set[str]:
                cte_names = set()
                for m in re.finditer(r'\bWITH\s+([A-Za-z_][\w]*)\s+AS\s*\(', sql_text, flags=re.IGNORECASE):
                    cte_names.add(m.group(1))

                tables = set()
                for m in re.finditer(r'\bFROM\b\s+([^;]+?)(?=\bWHERE\b|\bGROUP\b|\bHAVING\b|\bORDER\b|$)', sql_text, flags=re.IGNORECASE | re.DOTALL):
                    clause = m.group(1)
                    for part in clause.split(','):
                        raw = part.strip()
                        if not raw or raw.startswith('('):
                            continue
                        first_token = raw.split()[0]
                        tbl = first_token.strip('`"')
                        if '.' in tbl:
                            tbl = tbl.split('.')[-1]
                        tables.add(tbl)

                for m in re.finditer(r'\bJOIN\s+([`"]?[\w\.]+[`"]?)', sql_text, flags=re.IGNORECASE):
                    raw = m.group(1).strip()
                    tbl = raw.strip('`"')
                    if '.' in tbl:
                        tbl = tbl.split('.')[-1]
                    tables.add(tbl)

                return {t for t in tables if t not in cte_names}

            ok, explain_json = run_explain(sql, database or settings.mysql_database)

            # 1) 优先用 LLM（中文提示词）
            table_candidates: set[str] = ask_llm_for_tables(sql, explain_json if ok else None)

            # 2) LLM 为空则回退到 EXPLAIN JSON 的确定性解析
            if not table_candidates and ok and explain_json:
                table_candidates = _extract_tables_from_explain_json(explain_json)

            # 3) 再不行就用正则兜底
            if not table_candidates:
                table_candidates = _parse_table_names(sql)

            if not table_candidates:
                stats["collection_errors"].append("无法从 SQL/EXPLAIN/LLM 解析出表名，统计信息为空")

            normalized = set()
            for t in table_candidates:
                t = t.strip('`"')
                if '.' in t:
                    t = t.split('.')[-1]
                normalized.add(t)

            # 先在 table_statistics 中为每张表建立占位，随后采集覆盖
            for tbl in normalized:
                stats["table_statistics"].setdefault(tbl, {})

            for tbl in normalized:
                res = mysql_utils.get_mysql_table_statistics(tbl, database or settings.mysql_database)
                if res.get("success"):
                    stats["table_statistics"][tbl] = res.get("statistics", {})
                else:
                    stats["collection_errors"].append(f"获取表 {tbl} 统计信息失败: {res.get('error', '未知错误')}")

            stats["collection_success"] = len(stats["table_statistics"]) > 0 and len(stats["collection_errors"]) == 0
            return stats
        except Exception as e:
            stats["collection_errors"].append(f"MySQL统计信息获取失败: {e}")
            return stats

    # 如果没有 MySQL，返回空统计
    stats["collection_errors"].append("未配置 MySQL，统计信息不可用")
    return stats