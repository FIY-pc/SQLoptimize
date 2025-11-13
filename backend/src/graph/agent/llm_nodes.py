from typing import Optional, Dict, Any
import re
import logging
from src.graph.state import SQLState
from src.graph.tools.format import write_newline_to_stream, write_separator_to_stream

logger = logging.getLogger(__name__)

async def llm_equivalence_check(state: SQLState, sql1: str, sql2: str, db_schema: Optional[str] = None) -> Dict[str, Any]:
    logger.debug(f"call llm_equivalence_check")
    messages = [
        {
            "role": "system",
            "content": (
                "你是 SQL 语义等价性验证器。请基于给定的数据库 schema，判断两个 SQL 查询是否语义等价（返回的结果集在所有数据状态下相同）。\n"
                "- 必须从语义层面分析：连接、过滤、分组、聚合、去重、排序、NULL 处理、表达式等；不要仅凭格式或重命名。\n"
                "- 若存在不确定或依赖具体数据分布的情况，请谨慎处理，尽量避免误判为等价。\n"
                '- 仅返回 JSON：{"equivalent": true/false, "reason": "不等价的具体原因或分析"}，不要包含其他文本。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"数据库 schema（DDL）：\n```sql\n{db_schema or ''}\n```\n\n"
                f"SQL1：\n```sql\n{sql1}\n```\n\n"
                f"SQL2：\n```sql\n{sql2}\n```\n\n"
                "请判断两者是否语义等价，仅返回 JSON。"
            ),
        },
    ]
    try:
        llm = state.get("llm")
        content = await llm.chat_async(messages)
        import re, json
        m = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        json_str = m.group(1) if m else content
        result = json.loads(json_str)
        return {
            "success": True,
            "equivalent": bool(result.get("equivalent", False)),
            "reason": str(result.get("reason") or ""),
        }
    except Exception as e:
        logger.error(f"Error in llm_equivalence_check: {e}")
        return {
            "success": False,
            "equivalent": False,
            "reason": "",
            "error": str(e),
        }

async def final_report_node(state: SQLState) -> SQLState:
    """
    LLM Node: FinalReport
    整合多个优化方案的结果并输出综合报告
    """
    logger.debug(f"call final_report_node")
    sql = (state.get("sql") or "").strip()
    plans = state.get("optimization_plans", [])
    cost_before = state.get("cost_before")
    
    # 构建方案比较信息
    plans_info = ""
    best_plan = None
    best_cost_reduction = 0
    
    for i, plan in enumerate(plans):
        plan_id = plan.get("plan_id", f"plan{i+1}")
        description = plan.get("description", "")
        optimized_sql = plan.get("optimized_sql", "")
        reasoning = plan.get("reasoning", "")
        is_equivalent = plan.get("equivalence", False)
        cost = plan.get("cost")
        
        plans_info += f"\n## 方案 {i+1}: {plan_id}\n"
        plans_info += f"- 描述: {description}\n"
        plans_info += f"- 等价性: {'通过' if is_equivalent else '未通过'}\n"
        
        if is_equivalent and cost is not None and cost_before is not None:
            cost_reduction = cost_before - cost
            cost_reduction_percent = (cost_reduction / cost_before) * 100 if cost_before > 0 else 0
            plans_info += f"- 成本: {cost} (原始: {cost_before}, 减少: {cost_reduction:.2f}, {cost_reduction_percent:.2f}%)\n"
            
            # 记录最佳方案
            if is_equivalent and cost_reduction > best_cost_reduction:
                best_cost_reduction = cost_reduction
                best_plan = plan
        else:
            plans_info += f"- 成本: {'未评估' if not is_equivalent else '评估失败'}\n"
        
        plans_info += f"- SQL: ```sql\n{optimized_sql}\n```\n"
        plans_info += f"- 优化理由: {reasoning}\n"
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深TXSQL数据库性能优化专家。请根据提供的信息生成一份详细的SQL优化报告，比较不同优化方案的优缺点。\n"
                "标题为TXSQL优化报告"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始SQL:\n```sql\n{sql}\n```\n\n"
                f"优化方案比较:\n{plans_info}\n\n"
                "请提供一份详细的优化报告，包括:\n"
                "1. 先以表格形式输出原始sql的查询计划（即在数据库中执行原始sql的explain结果），然后对原始SQL的问题进行分析\n"
                "2. 各个优化方案的优化后sql，方案比较和成本对比，注意：必须根据优化方案比较中的成本对比输出改写前后的query_cost值\n\n"
                "请以Markdown格式返回报告。"
            ),
        },
    ]
    
    try:
        llm = state.get("llm")
        report = await llm.chat_async(messages)
        state["final_report"] = report
        # state.setdefault("history", []).append("[report] 已生成最终优化报告")
    except Exception as e:
        logger.error(f"Error in final_report_node: {e}")
        state["final_report"] = f"生成报告失败: {str(e)}"
        # state.setdefault("history", []).append(f"[report] 生成报告失败: {str(e)}")
    
    return state


async def generate_optimization_plans(state: SQLState) -> SQLState:
    """
    LLM Node: GenerateOptimizationPlans
    生成多个SQL优化方案
    输入：state["sql"], state["plan"], state["stats"], state["db_schema"]
    输出：state["optimization_plans"]
    """
    logger.debug(f"call generate_optimization_plans")
    sql = (state.get("sql") or "").strip()
    plan = (state.get("plan") or "").strip()
    stats = state.get("stats") or {}
    db_schema = (state.get("db_schema") or "").strip()

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深MySQL数据库性能优化专家。请分析用户提供的SQL，并提出两种不同的优化方案：\n"
                "- 必须依据提供的查询计划（EXPLAIN）与数据库统计信息（如表行数、索引、列选择性等）进行优化决策；\n"
                "- 两种方案必须采用不同的优化思路，例如：一种基于索引优化，另一种基于查询重构；或一种基于连接顺序调整，另一种基于子查询优化等；\n"
                "- 优化目标：以降低 EXPLAIN JSON 中 query_block.cost_info.query_cost 为首要目标，且不改变结果集语义；\n"
                "- 优化策略：考虑索引使用与覆盖、谓词下推、调整连接顺序（基数驱动）、去除冗余子句/子查询、避免函数使索引失效、减少不必要的 DISTINCT/ORDER BY/FILESORT/TEMPORARY；\n"
                "- 兼容性与规范要求（严格遵循 Apache Calcite/ANSI SQL）：\n"
                "  1) 禁止使用方言特性：反引号`、LIMIT、非标准函数、Hint、方言注释/语法；\n"
                "  2) 如需限制行数，请使用标准语法：OFFSET <n> ROWS FETCH FIRST <m> ROWS ONLY；\n"
                "  3) 标识符与关键字大小写：不得更改输入 SQL 中标识符的大小写；不要引入反引号；如必须引用标识符，仅使用 ANSI 的双引号；\n"
                "  4) 仅使用 ANSI 标准函数与语法；任何可能不被 Calcite 接受的写法，必须纠正为可解析的标准写法；\n"
                "  5) 每个方案的 optimized_sql 必须是 Calcite 可解析的 SQL。\n"
                "- 输出要求：以 Markdown 格式返回两种优化方案（不要 JSON，不要使用 ```json```）。\n"
                "  先输出一个一级大标题：\"# SQL初始优化方案总览\"，并用1-2句话简述整体优化目标与两种方案的思路差异；\n"
                "  随后严格按以下固定结构输出每个方案（保持标签不变，便于解析）：\n"
                "  ## 方案1\n"
                "  - 描述: <一句话或短段落>\n"
                "  - 优化后的SQL:\n"
                "  ```sql\n"
                "  <SQL>\n"
                "  ```\n"
                "  - 优化理由:\n"
                "  <多段文字，引用 EXPLAIN 与统计信息证据，解释如何降低 query_cost>\n"
                "  \n\n"
                "  然后以同样格式输出 plan2（标题必须为 '## 方案2'）。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始 SQL：\n```sql\n{sql}\n```\n\n"
                f"数据库 schema（DDL）：\n```sql\n{db_schema}\n```\n\n"
                f"查询计划：\n{plan}\n\n"
                f"统计信息（JSON）：\n```json\n{stats}\n```\n\n"
                "请先输出 '# SQL初始优化方案总览' 作为大标题，给出一句话的整体说明，"
                "然后严格按上述 Markdown 结构输出 '## 方案 plan1' 与 '## 方案 plan2'。仅返回 Markdown，不要其他说明。"
            ),
        },
    ]

    try:
        llm = state.get("llm")
        content = await llm.chat_async(messages)

        # 从 Markdown 结构解析
        plans = _extract_plans_from_markdown(content)

        state["optimization_plans"] = plans
        state["current_plan_index"] = 0

        if plans:
            state["optimized_sql"] = plans[0].get("optimized_sql", "")

        # 末尾换行
        await write_newline_to_stream()
        await write_separator_to_stream()
    except Exception as e:
        logger.error(f"Error in generate_optimization_plans: {e}")

    return state


def _extract_plans_from_markdown(md: str) -> list[dict]:
    """
    解析固定结构的 Markdown，提取 [plan_id, description, optimized_sql, reasoning]。
    """
    plans = []
    sections = list(re.finditer(r"^##\s*方案\s*(?:plan)?\s*(\d+)\s*$", md, re.MULTILINE))
    for i, m in enumerate(sections):
        start = m.start()
        end = sections[i + 1].start() if (i + 1) < len(sections) else len(md)
        section = md[start:end]
        plan_num = m.group(1) if m and m.group(1) else str(i + 1)
        plan_id = f"plan{plan_num}"

        # 描述
        m_desc = re.search(r"-\s*描述\s*:\s*(.*)", section)
        description = m_desc.group(1).strip() if m_desc else ""

        # SQL（取第一个 ```sql``` 代码块）
        m_sql = re.search(r"```sql\s*(.*?)\s*```", section, re.IGNORECASE | re.DOTALL)
        optimized_sql = (m_sql.group(1).strip().rstrip(";") if m_sql else "")

        # 优化理由（从 “- 优化理由:” 标签后到该段落末尾）
        m_reason_label = re.search(r"-\s*优化理由\s*:\s*", section)
        reasoning = section[m_reason_label.end():].strip() if m_reason_label else ""

        plans.append({
            "plan_id": plan_id,
            "description": description,
            "optimized_sql": optimized_sql,
            "reasoning": reasoning,
            "equivalence": False,
            "cost": None,
            "eq_fix_attempts": 0
        })
    return plans


def _extract_sql_from_text(text: str) -> str:
    m = re.search(r"```sql\s*(.*?)\s*```", text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip().rstrip(";")
    m2 = re.search(r"((?:SELECT|WITH)\s.*?)(?:```|$)", text, re.IGNORECASE | re.DOTALL)
    return (m2.group(1).strip().rstrip(";") if m2 else "")


async def fix_sql_with_explain_error(state: SQLState) -> SQLState:
    logger.debug("call fix_sql_with_explain_error")
    current_index = int(state.get("current_plan_index", 0))
    plans = state.get("optimization_plans", [])
    error_msg = (state.get("explain_error") or "").strip()
    db_schema = (state.get("db_schema") or "").strip()

    optimized_sql = (state.get("optimized_sql") or "").strip()
    if 0 <= current_index < len(plans):
        optimized_sql = (plans[current_index].get("optimized_sql") or optimized_sql or "").strip()
    # 根据当前方案提取 plan_id 的显示编号
    plan_id = ""
    if 0 <= current_index < len(plans):
        plan_id = (plans[current_index].get("plan_id") or "").strip()
    import re
    m = re.search(r"\d+", plan_id)
    plan_display = m.group(0) if m else (plan_id or str(current_index + 1))

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深MySQL数据库性能优化专家。根据数据库返回的 EXPLAIN 错误信息，对给定 SQL 进行修复，"
                "保证能在目标数据库执行，同时保持与原查询语义等价。"
                "请严格按照如下固定格式输出，不要标题、不要额外说明、不要 JSON：\n"
                f"#### 初始优化方案{plan_display}的SQL存在{{错误类别}}：{{错误摘要}},修复后的SQL为：\n"
                "```sql\n"
                "<修复后的SQL>\n"
                "```\n\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"当前优化后的 SQL：\n```sql\n{optimized_sql}\n```\n\n"
                f"数据库返回的 EXPLAIN 错误信息：\n{error_msg}\n\n"
                "请依据 EXPLAIN 错误信息提炼“错误类别”（如解析错误/语法错误/语义错误/类型错误/标识符不存在等）与“错误摘要”，严禁编造新原因。\n"
                "保证修复后的 SQL 与原查询语义等价，且符合 ANSI/Calcite 解析。\n"
                "请严格按照如下固定格式输出，不要标题、不要额外说明、不要 JSON：\n"
                f"##### 初始优化方案{plan_display}的SQL存在{{错误类别}}：{{错误摘要}}，修复后的SQL为：\n"
                "```sql\n"
                "<修复后的SQL>\n"
                "```\n\n"
            ),
        },
    ]

    try:
        llm = state.get("llm")
        content = await llm.chat_async(messages)
        fixed_sql = _extract_sql_from_text(content)

        if fixed_sql:
            state["optimized_sql"] = fixed_sql
            if 0 <= current_index < len(plans):
                plans[current_index]["optimized_sql"] = fixed_sql
                state["optimization_plans"] = plans
            # 只有成功修复后才清理错误并关闭修复标记
            state["need_fix_sql"] = False
            state["explain_error"] = ""
        else:
            # 未能提取到修复 SQL，保留修复标记，便于再次尝试
            state["need_fix_sql"] = True
    except Exception as e:
        logger.error(f"fix_sql_with_explain_error failed: {e}")
        # 发生异常时继续保持需要修复状态
        state["need_fix_sql"] = True

    await write_newline_to_stream()
    await write_separator_to_stream()
    return state


async def fix_sql_with_equivalence_reason(state: SQLState) -> SQLState:
    logger.debug("call fix_sql_with_equivalence_reason")
    current_index = int(state.get("current_plan_index", 0))
    plans = state.get("optimization_plans", [])
    orig_sql = (state.get("sql") or "").strip()
    db_schema = (state.get("db_schema") or "").strip()

    # 取当前方案和最近一次原因
    plan_sql = ""
    plan_reason = (state.get("equivalence_reason") or "").strip()
    if 0 <= current_index < len(plans):
        plan_sql = (plans[current_index].get("optimized_sql") or "").strip()
        if not plan_reason:
            plan_reason = (plans[current_index].get("equivalence_reason") or "").strip()

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深MySQL/ANSI SQL专家。基于提供的“等价性不通过原因”，修复给定的优化后SQL，使其与原始SQL在语义上等价。\n"
                "要求：\n"
                "- 优先使用 MySQL 8.0 语法，避免方言不兼容；\n"
                "- 修复后尽量保持优化思路（如索引使用、连接顺序调整等）；\n"
                "- 仅返回一个 ```sql ... ``` 代码块，不要包含其他文本。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始 SQL：\n```sql\n{orig_sql}\n```\n\n"
                f"当前优化后的 SQL（待修复）：\n```sql\n{plan_sql}\n```\n\n"
                f"不等价原因：\n{plan_reason}\n\n"
                "请输出修复后的 SQL，仅以 ```sql ... ``` 代码块返回。"
            ),
        },
    ]

    try:
        llm = state.get("llm")
        content = await llm.chat_async(messages)
        fixed_sql = _extract_sql_from_text(content)

        # 累加当前方案的修复尝试次数
        if 0 <= current_index < len(plans):
            plans[current_index]["eq_fix_attempts"] = int(plans[current_index].get("eq_fix_attempts", 0)) + 1

        if fixed_sql:
            state["optimized_sql"] = fixed_sql
            if 0 <= current_index < len(plans):
                plans[current_index]["optimized_sql"] = fixed_sql
                plans[current_index]["equivalence_reason"] = ""
                state["optimization_plans"] = plans
            state["need_fix_equivalence"] = False
        else:
            state["need_fix_equivalence"] = True  # 没取到SQL，再尝试一次
        # 累加迭代计数，用于回路收敛
        state["iteration_count"] = int(state.get("iteration_count", 0)) + 1
    except Exception as e:
        logger.error(f"fix_sql_with_equivalence_reason failed: {e}")
        state["need_fix_equivalence"] = True

    await write_newline_to_stream()
    return state