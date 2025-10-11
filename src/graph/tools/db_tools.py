from typing import Dict, Any, Optional, Tuple
import json

from src.config import get_settings
from graph.state import SQLState


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
            # 从 SQL 中解析表名（FROM / JOIN），并收集这些表的统计信息
            import re
            table_candidates = set()
            patterns = [
                r'\bFROM\s+([`"]?[\w\.]+[`"]?)',
                r'\bJOIN\s+([`"]?[\w\.]+[`"]?)',
            ]
            for pat in patterns:
                for m in re.finditer(pat, sql, flags=re.IGNORECASE):
                    raw = m.group(1).strip()
                    tbl = raw.strip('`"')
                    if '.' in tbl:
                        tbl = tbl.split('.')[-1]
                    tbl = tbl.split()[0]
                    table_candidates.add(tbl)

            if not table_candidates:
                stats["collection_errors"].append("无法从 SQL 解析出表名，统计信息为空")

            for tbl in table_candidates:
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