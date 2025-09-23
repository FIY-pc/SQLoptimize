import re
import sqlite3
import json
import subprocess
import os
import shutil

from src.graph.state import State
from src.llm import get_llm
from src.config import get_settings
from src.utils.mysql_utils import MySQLUtils


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
    - 优先使用MySQL数据库获取真实执行计划；
    - 若MySQL不可用，则使用SQLite的EXPLAIN QUERY PLAN；
    - 最后使用LLM对SQL进行静态分析。
    """
    _ensure_history(state)
    sql = (state.get("optimized_sql") or state.get("input_sql") or "").strip()
    if not sql:
        state["history"].append("[plan] 无 SQL 可检查")
        return state

    settings = get_settings()

    # 优先尝试MySQL执行计划
    if settings.mysql_host and settings.mysql_user:
        try:
            # 首先测试连接
            # TODO: 这里现在是直接加载配置的MySQL，但是API要求用户能用自己的数据库，所以给后端用可能要改改
            mysql_utils = MySQLUtils.create_from_settings()
            conn_test = mysql_utils.test_mysql_connection()
            if conn_test["success"]:
                state["history"].append(f"[plan] 已连接到MySQL: {conn_test.get('version', 'Unknown')}")

                # 获取执行计划
                database = settings.mysql_database or state.get("target_database")
                plan_result = mysql_utils.get_mysql_explain_plan(sql, database)

                if plan_result["success"]:
                    explain_json = plan_result.get("explain_json")
                    explain_traditional = plan_result.get("explain_traditional", [])

                    # 格式化执行计划输出
                    feedback_parts = []

                    if explain_json:
                        feedback_parts.append("MySQL执行计划 (JSON格式):")
                        feedback_parts.append(json.dumps(explain_json, indent=2, ensure_ascii=False))

                    if explain_traditional:
                        feedback_parts.append("\nMySQL执行计划 (传统格式):")
                        for row in explain_traditional:
                            if isinstance(row, dict):
                                row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                            else:
                                row_str = " | ".join(str(col) for col in row)
                            feedback_parts.append(row_str)

                    state["plan_feedback"] = "\n".join(feedback_parts)
                    state["mysql_plan_result"] = plan_result
                    state["history"].append("[plan] 已使用MySQL EXPLAIN获取执行计划")
                    return state
                else:
                    state["history"].append(f"[plan] MySQL执行计划获取失败: {plan_result.get('error', '未知错误')}")
            else:
                state["history"].append(f"[plan] MySQL连接测试失败: {conn_test.get('error', '未知错误')}")
        except Exception as e:
            state["history"].append(f"[plan] MySQL执行计划异常: {e}")

    # 回退到SQLite
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


def verify_node(state: State) -> State:
    """验证节点：使用SQL等价性校验工具验证优化前后的SQL是否语义等价。"""
    
    _ensure_history(state)
    input_sql = state.get("input_sql", "").strip()
    optimized_sql = state.get("optimized_sql", "").strip()
    
    if not input_sql or not optimized_sql:
        state["history"].append("[verify] 缺少输入SQL或优化SQL，跳过验证")
        state["verification_result"] = {"success": False, "error": "缺少必要的SQL"}
        return state
    
    # 获取配置
    settings = get_settings()
    jar_path = settings.sqlsolver_jar_path or '/media/sata3/jgy/SQL/SQL等价性校验/lib/sqlsolver-v1.1.0.jar'
    z3_lib_path = settings.z3_lib_path or '/media/sata3/jgy/SQL/SQL等价性校验/lib'
    schema = state.get("schema", "CREATE TABLE users(id INT, age INT);")  # 默认schema，应从配置获取
    
    # 调用SQL等价性验证
    try:
        result = _verify_sql_equivalence(jar_path, input_sql, optimized_sql, schema, java_path=settings.java_17_path, z3_lib_path=z3_lib_path)
        state["verification_result"] = result
        
        if result["success"]:
            is_equivalent = result.get("equivalent", False)
            state["history"].append(f"[verify] SQL等价性验证完成：{'等价' if is_equivalent else '不等价'}")
        else:
            state["history"].append(f"[verify] 验证失败：{result.get('error', '未知错误')}")
    except Exception as e:
        state["verification_result"] = {"success": False, "error": f"验证异常：{e}"}
        state["history"].append(f"[verify] 验证异常：{e}")
    
    return state


def _verify_sql_equivalence(jar_path, sql1, sql2, schema, java_path=None, z3_lib_path="./lib"):
    """SQL等价性验证工具函数"""
    # 1. 处理Java路径
    if java_path:
        if not os.path.isfile(java_path) or not os.access(java_path, os.X_OK):
            return {"success": False, "error": f"无效的Java路径: {java_path}"}
        java_executable = java_path
    else:
        java_executable = shutil.which("java")
        if not java_executable:
            return {"success": False, "error": "未找到Java环境，请安装或指定java_path"}

    # 2. 处理JAR包路径
    absolute_jar_path = os.path.abspath(jar_path)
    if not os.path.exists(absolute_jar_path):
        return {"success": False, "error": f"JAR包不存在: {absolute_jar_path}"}

    # 3. 处理Z3库路径
    env = os.environ.copy()
    if z3_lib_path:
        if not os.path.isdir(z3_lib_path):
            return {"success": False, "error": f"Z3库目录不存在: {z3_lib_path}"}
        if os.name == "posix":
            lib_env = "LD_LIBRARY_PATH" if os.uname().sysname != "Darwin" else "DYLD_LIBRARY_PATH"
            abs_z3 = os.path.abspath(z3_lib_path)
            env[lib_env] = abs_z3 if not env.get(lib_env) else f"{abs_z3}:{env.get(lib_env)}"

    # 4. 构建命令
    command = [
        java_executable,
        f"-Djava.library.path={os.path.abspath(z3_lib_path)}",
        "-jar",
        absolute_jar_path,
        "-sql1", sql1,
        "-sql2", sql2,
        "-schema", schema
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "未知错误"
            return {"success": False, "error": f"执行失败: {error_msg}"}

        output = result.stdout.strip()
        equivalent = None
        details = output

        # 解析结果
        for line in output.splitlines():
            if "SQL等价性验证结果: " in line:
                if "NEQ" in line:
                    equivalent = False
                elif "EQ" in line:
                    equivalent = True
                break

        if equivalent is not None:
            return {
                "success": True,
                "equivalent": bool(equivalent),
                "details": details
            }
        else:
            return {
                "success": False,
                "error": "无法从输出解析出SQL等价性结果",
                "raw_output": output
            }
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时（60s）"}
    except Exception as e:
        return {"success": False, "error": f"未知异常: {e}"}


def output_node(state: State) -> State:
    """输出节点：整理最终输出并记录。"""
    _ensure_history(state)
    has_opt = bool(state.get("optimized_sql"))
    has_plan = bool(state.get("plan_feedback"))
    has_verify = bool(state.get("verification_result"))
    state["history"].append(
        f"[output] 输出就绪：optimized_sql={'Y' if has_opt else 'N'}, plan_feedback={'Y' if has_plan else 'N'}, verification={'Y' if has_verify else 'N'}"
    )
    return state