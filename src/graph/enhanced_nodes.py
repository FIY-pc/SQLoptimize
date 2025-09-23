"""增强的节点功能，支持智能分析、多轮改写和错误反馈"""

import re
import json
import logging

from src.graph.state import State
from src.llm import get_llm
from src.config import get_settings
from src.utils.mysql_utils import MySQLUtils
from src.graph.sql_analyzer import analyze_sql_with_statistics, format_statistics_for_llm

logger = logging.getLogger(__name__)


def _ensure_history(state: State) -> None:
    """确保状态中有历史记录"""
    if "history" not in state or state["history"] is None:
        state["history"] = []


def _ensure_iteration_context(state: State) -> None:
    """确保迭代上下文存在"""
    if "iteration_count" not in state:
        state["iteration_count"] = 0
    if "optimization_errors" not in state:
        state["optimization_errors"] = []
    if "previous_attempts" not in state:
        state["previous_attempts"] = []


def enhanced_input_node(state: State) -> State:
    """增强的输入节点：收集SQL统计信息"""
    _ensure_history(state)
    _ensure_iteration_context(state)

    sql = state.get("input_sql", "").strip()
    if not sql:
        state["history"].append("[input] 未提供 input_sql")
        return state

    state["history"].append(f"[input] 接收到 SQL: {sql[:200]}{'...' if len(sql) > 200 else ''}")

    # 分析SQL并收集统计信息
    try:
        settings = get_settings()
        database = settings.mysql_database or state.get("target_database")

        analysis, statistics = analyze_sql_with_statistics(sql, database)

        state["sql_analysis"] = analysis
        state["table_statistics"] = statistics
        state["formatted_statistics"] = format_statistics_for_llm(statistics)

        if statistics.get("collection_success"):
            table_count = len(statistics.get("table_statistics", {}))
            state["history"].append(f"[input] 已收集 {table_count} 个表的统计信息")
        else:
            state["history"].append(f"[input] 统计信息收集部分失败: {len(statistics.get('collection_errors', []))} 个错误")

    except Exception as e:
        state["history"].append(f"[input] 统计信息收集异常: {e}")
        logger.error(f"统计信息收集异常: {e}")

    return state


def enhanced_optimize_node(state: State) -> State:
    """增强的优化节点：基于统计信息和执行计划进行智能优化"""
    _ensure_history(state)
    _ensure_iteration_context(state)

    input_sql = state.get("input_sql", "").strip()
    if not input_sql:
        state["history"].append("[optimize] 缺少输入 SQL，跳过优化")
        return state

    state["iteration_count"] += 1
    iteration = state["iteration_count"]

    # 获取统计信息和执行计划
    statistics_info = state.get("formatted_statistics", "")
    plan_feedback = state.get("plan_feedback", "")

    # 构建增强的优化提示
    prompt_system = _build_enhanced_system_prompt()
    prompt_user = _build_enhanced_user_prompt(
        input_sql, statistics_info, plan_feedback,
        state.get("optimization_errors", []),
        state.get("previous_attempts", []),
        iteration
    )

    # 组装消息
    messages = [
        {"role": "system", "content": prompt_system},
        {"role": "user", "content": prompt_user},
    ]

    # 注入自定义改写规则
    rewrite_rules = state.get("rewrite_rules")
    if rewrite_rules:
        try:
            rules_json = json.dumps(rewrite_rules, ensure_ascii=False, indent=2)
            count = len(rewrite_rules.get("rules", [])) if isinstance(rewrite_rules, dict) else 0
            state["history"].append(f"[optimize] 将 {count} 条自定义规则注入 LLM")
            messages.append({
                "role": "user",
                "content": f"自定义改写规则（严格参考但不要改变查询语义）：\n```json\n{rules_json}\n```"
            })
        except Exception:
            pass

    # 调用LLM进行优化
    try:
        llm = get_llm()
        content = llm.chat(messages)
        optimized_sql = _extract_sql_from_text(content)

        state["optimized_sql"] = optimized_sql
        state["previous_attempts"].append({
            "iteration": iteration,
            "sql": optimized_sql,
            "reasoning": content
        })

        state["history"].append(f"[optimize] 第 {iteration} 轮优化完成")

    except Exception as e:
        state["optimization_errors"].append(f"第 {iteration} 轮优化失败: {e}")
        state["history"].append(f"[optimize] 第 {iteration} 轮优化失败: {e}")
        logger.error(f"优化失败: {e}")

    return state


def syntax_check_node(state: State) -> State:
    """语法检查节点：验证SQL语法正确性"""
    _ensure_history(state)
    _ensure_iteration_context(state)

    optimized_sql = state.get("optimized_sql", "").strip()
    if not optimized_sql:
        state["history"].append("[syntax] 无优化SQL可检查")
        return state

    # 简单的语法检查
    syntax_errors = []

    # 基本语法检查
    if not _basic_syntax_check(optimized_sql):
        syntax_errors.append("基本SQL语法错误")

    # 尝试用MySQL验证语法（如果可用）
    mysql_syntax_error = _check_mysql_syntax(optimized_sql)
    if mysql_syntax_error:
        syntax_errors.append(f"MySQL语法错误: {mysql_syntax_error}")

    state["syntax_errors"] = syntax_errors
    state["syntax_valid"] = len(syntax_errors) == 0

    if syntax_errors:
        state["optimization_errors"].extend(syntax_errors)
        state["history"].append(f"[syntax] 发现 {len(syntax_errors)} 个语法错误")
    else:
        state["history"].append("[syntax] 语法检查通过")

    return state


def quality_assessment_node(state: State) -> State:
    """质量评估节点：评估改写质量并决定是否需要重新优化"""
    _ensure_history(state)
    _ensure_iteration_context(state)

    input_sql = state.get("input_sql", "")
    optimized_sql = state.get("optimized_sql", "")
    syntax_valid = state.get("syntax_valid", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = 3  # 最大迭代次数

    assessment = {
        "should_retry": False,
        "retry_reason": "",
        "quality_score": 0,
        "improvements": []
    }

    # 语法错误检查
    if not syntax_valid:
        if iteration_count < max_iterations:
            assessment["should_retry"] = True
            assessment["retry_reason"] = "语法错误需要修正"
        else:
            assessment["retry_reason"] = "达到最大迭代次数，语法仍有错误"

    # 等价性检查结果
    verification_result = state.get("verification_result", {})
    if verification_result.get("success") and not verification_result.get("equivalent"):
        if iteration_count < max_iterations:
            assessment["should_retry"] = True
            assessment["retry_reason"] = "SQL不等价需要修正"
        else:
            assessment["retry_reason"] = "达到最大迭代次数，等价性仍有问题"

    # 性能评估（简化版）
    if input_sql and optimized_sql and syntax_valid:
        quality_score = _evaluate_optimization_quality(input_sql, optimized_sql, state)
        assessment["quality_score"] = quality_score

        if quality_score < 60 and iteration_count < max_iterations:
            assessment["should_retry"] = True
            assessment["retry_reason"] = f"优化质量较低 ({quality_score}/100)"

    state["quality_assessment"] = assessment
    state["history"].append(f"[quality] 质量评估完成，分数: {assessment['quality_score']}")

    if assessment["should_retry"]:
        state["history"].append(f"[quality] 需要重新优化: {assessment['retry_reason']}")

    return state


def reflection_node(state: State) -> State:
    """反思节点：分析错误并为下一轮优化提供指导"""
    _ensure_history(state)
    _ensure_iteration_context(state)

    should_retry = state.get("quality_assessment", {}).get("should_retry", False)
    if not should_retry:
        state["history"].append("[reflection] 无需反思，优化已完成")
        return state

    # 收集错误信息
    errors = []
    errors.extend(state.get("syntax_errors", []))
    errors.extend(state.get("optimization_errors", []))

    verification_result = state.get("verification_result", {})
    if verification_result.get("success") and not verification_result.get("equivalent"):
        errors.append("SQL语义不等价")

    # 生成反思指导
    reflection_prompt = _build_reflection_prompt(
        state.get("input_sql", ""),
        state.get("optimized_sql", ""),
        errors,
        state.get("previous_attempts", [])
    )

    try:
        llm = get_llm()
        reflection_content = llm.chat([
            {"role": "system", "content": "你是SQL优化专家。请分析优化失败的原因并提供改进建议。"},
            {"role": "user", "content": reflection_prompt}
        ])

        state["reflection_guidance"] = reflection_content
        state["history"].append("[reflection] 已生成改进指导")

    except Exception as e:
        state["history"].append(f"[reflection] 反思失败: {e}")
        logger.error(f"反思失败: {e}")

    return state


def _extract_sql_from_text(text: str) -> str:
    """从文本中提取SQL代码"""
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


def _build_enhanced_system_prompt() -> str:
    """构建增强的系统提示"""
    return """你是一名资深数据库性能优化专家，专精于SQL查询优化。

你的任务是基于以下信息对SQL进行智能优化：
1. 原始SQL语句
2. 表统计信息（行数、数据大小、索引信息）
3. 执行计划分析
4. 性能瓶颈识别
5. 历史优化尝试和错误信息

优化原则：
- 保持SQL语义完全等价
- 优先解决性能瓶颈（大表扫描、缺失索引、复杂JOIN）
- 考虑数据分布和索引利用率
- 避免引入语法错误
- 如果之前的尝试有错误，必须修正这些错误

输出要求：
- 只输出最终的优化SQL
- 使用 ```sql 代码块包裹
- 在代码前简要说明主要优化点"""


def _build_enhanced_user_prompt(input_sql: str, statistics: str, plan: str,
                               errors: list, previous_attempts: list, iteration: int) -> str:
    """构建增强的用户提示"""
    prompt_parts = [f"【第 {iteration} 轮优化】"]

    # 原始SQL
    prompt_parts.append(f"原始SQL：\n```sql\n{input_sql}\n```")

    # 统计信息
    if statistics:
        prompt_parts.append(f"表统计信息：\n{statistics}")

    # 执行计划
    if plan:
        prompt_parts.append(f"执行计划分析：\n{plan}")

    # 错误信息
    if errors:
        prompt_parts.append(f"需要修正的错误：\n" + "\n".join(f"- {error}" for error in errors))

    # 历史尝试
    if previous_attempts:
        prompt_parts.append("历史优化尝试：")
        for attempt in previous_attempts[-2:]:  # 只显示最近2次
            prompt_parts.append(f"第 {attempt['iteration']} 轮: {attempt['sql'][:100]}...")

    prompt_parts.append("请根据以上信息进行智能优化，确保语义等价且性能更优。")

    return "\n\n".join(prompt_parts)


def _build_reflection_prompt(input_sql: str, optimized_sql: str, errors: list, attempts: list) -> str:
    """构建反思提示"""
    prompt_parts = [
        "请分析以下SQL优化过程中的问题：",
        f"原始SQL: {input_sql}",
        f"当前优化SQL: {optimized_sql}",
        f"遇到的错误: {'; '.join(errors)}",
        f"历史尝试次数: {len(attempts)}",
        "",
        "请提供具体的改进建议，包括：",
        "1. 错误原因分析",
        "2. 具体修正方法",
        "3. 优化策略调整建议"
    ]
    return "\n".join(prompt_parts)


def _basic_syntax_check(sql: str) -> bool:
    """基本SQL语法检查"""
    sql = sql.strip().upper()

    # 基本结构检查
    if not sql:
        return False

    # 简单的关键字匹配
    if sql.startswith('SELECT'):
        return 'FROM' in sql
    elif sql.startswith(('INSERT', 'UPDATE', 'DELETE')):
        return True

    return False


def _check_mysql_syntax(sql: str) -> str:
    """使用MySQL检查语法（如果可用）"""
    try:
        settings = get_settings()
        if not (settings.mysql_host and settings.mysql_user):
            return ""

        # 尝试EXPLAIN语法检查（不实际执行）
        # TODO: 这里现在是直接加载配置的MySQL，但是API要求用户能用自己的数据库，所以给后端用可能要改改
        mysql_utils = MySQLUtils.create_from_settings() 
        result = mysql_utils.get_mysql_explain_plan(sql)
        if not result["success"]:
            return result.get("error", "MySQL语法检查失败")

        return ""  # 语法正确

    except Exception as e:
        return f"MySQL语法检查异常: {e}"


def _evaluate_optimization_quality(input_sql: str, optimized_sql: str, state: State) -> int:
    """评估优化质量（简化版）"""
    score = 50  # 基础分

    # 长度比较（简化指标）
    if len(optimized_sql) < len(input_sql):
        score += 10

    # 关键字优化检查
    optimizations = [
        ('JOIN' in optimized_sql.upper() and 'WHERE' in optimized_sql.upper(), 15),
        ('INDEX' in optimized_sql.upper(), 10),
        ('LIMIT' in optimized_sql.upper(), 5),
        ('ORDER BY' in input_sql.upper() and 'ORDER BY' in optimized_sql.upper(), 5)
    ]

    for condition, points in optimizations:
        if condition:
            score += points

    return min(score, 100)