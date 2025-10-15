from typing import Optional, Dict, Any
from src.sql_equality.test import verify_sql_equivalence
from src.config import get_settings


def run_equivalence_checker(
    sql1: str,
    sql2: str,
    db_schema: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用现有的等价性校验工具封装（src/sql_equality/test.py）。
    返回字典：{ success: bool, equivalent: bool, details?: str, error?: str }
    """
    from src.config import get_settings
    settings = get_settings()
    jar_path = settings.sqlsolver_jar_path 
    z3_lib_path = settings.z3_lib_path 
    java_path = settings.java_17_path or None

    # 自动构建 schema（当未显式传入时）
    if not db_schema:
        try:
            import re
            from src.utils.mysql_utils import MySQLUtils

            def _parse_table_names(sql_text: str) -> set[str]:
                # 1) 收集 CTE 名称
                cte_names = set()
                for m in re.finditer(r'\bWITH\s+([A-Za-z_][\w]*)\s+AS\s*\(', sql_text, flags=re.IGNORECASE):
                    cte_names.add(m.group(1))

                tables = set()

                # 2) 解析所有 FROM 子句，提取逗号分隔的表项
                for m in re.finditer(
                    r'\bFROM\b\s+([^;]+?)(?=\bWHERE\b|\bGROUP\b|\bHAVING\b|\bORDER\b|$)',
                    sql_text,
                    flags=re.IGNORECASE | re.DOTALL
                ):
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

                # 3) 解析 JOIN 后的表
                for m in re.finditer(r'\bJOIN\s+([`"]?[\w\.]+[`"]?)', sql_text, flags=re.IGNORECASE):
                    raw = m.group(1).strip()
                    tbl = raw.strip('`"')
                    if '.' in tbl:
                        tbl = tbl.split('.')[-1]
                    tables.add(tbl)

                # 4) 排除 CTE 名称
                return {t for t in tables if t not in cte_names}

            table_names = _parse_table_names(sql1 + " " + sql2)

            schema_parts: list[str] = []
            mysql_utils = None
            # 优先尝试从 MySQL 拉取信息生成 DDL
            if settings.mysql_host and settings.mysql_user:
                try:
                    mysql_utils = MySQLUtils.create_from_settings()
                    # 确定数据库名
                    db_name = settings.mysql_database or None
                    for tbl in table_names:
                        res = mysql_utils.get_mysql_table_statistics(tbl, db_name)
                        if not res.get("success"):
                            continue
                        stats = res.get("statistics") or {}
                        cols = stats.get("columns") or []
                        idxs = stats.get("indexes") or []

                        col_defs = []
                        for col in cols:
                            name = f"`{col.get('COLUMN_NAME')}`"
                            dtype = (col.get("DATA_TYPE") or "varchar").lower()
                            # 补充长度/精度
                            length = col.get("CHARACTER_MAXIMUM_LENGTH")
                            precision = col.get("NUMERIC_PRECISION")
                            scale = col.get("NUMERIC_SCALE")
                            type_decl = dtype
                            if dtype in ("varchar", "char") and length:
                                type_decl = f"{dtype}({int(length)})"
                            elif dtype in ("decimal", "numeric") and precision is not None:
                                if scale is not None:
                                    type_decl = f"{dtype}({int(precision)},{int(scale)})"
                                else:
                                    type_decl = f"{dtype}({int(precision)})"
                            # 其他类型保持原样
                            not_null = " NOT NULL" if (col.get("IS_NULLABLE") == "NO") else ""
                            col_defs.append(f"{name} {type_decl}{not_null}")

                        # PRIMARY KEY
                        pk_cols: list[tuple[int, str]] = []
                        for idx in idxs:
                            if (idx.get("INDEX_NAME") or "").upper() == "PRIMARY":
                                seq = idx.get("SEQ_IN_INDEX") or 0
                                coln = idx.get("COLUMN_NAME")
                                if coln:
                                    pk_cols.append((int(seq), f"`{coln}`"))
                        pk_cols.sort(key=lambda x: x[0])
                        if pk_cols:
                            col_defs.append(f"PRIMARY KEY ({', '.join([c for _, c in pk_cols])})")

                        if col_defs:
                            joined_cols = ",\n  ".join(col_defs)
                            schema_parts.append(f"CREATE TABLE `{tbl}` (\n  {joined_cols}\n);")
                    # 若成功生成至少一个表的 DDL，则使用
                    if schema_parts:
                        db_schema = "\n".join(schema_parts)
                except Exception:
                    # MySQL 构建失败则继续尝试 TPCH
                    pass

            # 后备：TPCH 内置 schema（仅当匹配到已知表）
            if not db_schema:
                try:
                    from src.utils.mysql_utils import MySQLUtils as MU
                    tpch = getattr(MU, "TPCH_SCHEMA", {})
                    for tbl in table_names:
                        meta = tpch.get(tbl)
                        if not meta:
                            continue
                        cols = meta.get("columns") or []
                        pk = meta.get("primary_key") or []
                        col_defs = [f"`{c}` VARCHAR(255)" for c in cols]
                        if pk:
                            col_defs.append(f"PRIMARY KEY ({', '.join([f'`{c}`' for c in pk])})")
                        joined_cols = ",\n  ".join(col_defs)
                        schema_parts.append(f"CREATE TABLE `{tbl}` (\n  {joined_cols}\n);")
                    if schema_parts:
                        db_schema = "\n".join(schema_parts)
                except Exception:
                    pass
        except Exception:
            db_schema = None

    try:
        if not sql2:
            return {"success": False, "equivalent": False, "error": "缺少优化后SQL"}
        result = verify_sql_equivalence(
            jar_path,
            sql1,
            sql2,
            db_schema,
            java_path=java_path,
            z3_lib_path=z3_lib_path
        )
        # 适配返回结构
        if result.get("success"):
            return {
                "success": True,
                "equivalent": bool(result.get("equivalent", False)),
                "details": result.get("details", ""),
            }
        else:
            return {"success": False, "equivalent": False, "error": result.get("error", "未知错误")}
    except Exception as e:
        return {"success": False, "equivalent": False, "error": f"等价性验证异常: {e}"}