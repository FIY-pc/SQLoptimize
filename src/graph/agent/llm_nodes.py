from typing import Dict, Any, Optional
import re
import logging
from src.llm import get_llm

logger = logging.getLogger(__name__)

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

def _extract_explanation_from_text(text: str) -> str:
    """
    提取模型输出中 SQL 代码块之前的说明文本；若无代码块，则返回全文作为说明。
    """
    if not text:
        return ""
    m = re.search(r"```sql\s*\n(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        before = text[:m.start()].strip()
        return before.strip()
    return text.strip()

def optimize_sql_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM Node: OptimizeSQL
    输入：state["sql"], state["plan"], state["stats"]
    输出：state["optimized_sql"]
    """
    logger.debug(f"call optimize_sql_node")
    sql = (state.get("sql") or "").strip()
    plan = (state.get("plan") or "").strip()
    stats = state.get("stats") or {}
    db_schema = (state.get("db_schema") or "").strip()

    messages = [
        {
            "role": "system",
            "content": (
                "你是一名资深MySQL数据库性能优化专家。请在语义等价的前提下优化并规范化用户提供的 SQL：\n"
                "- 必须依据提供的查询计划（EXPLAIN）与数据库统计信息（如表行数、索引、列选择性等）进行优化决策；若统计信息缺失或不完整，请进行保守改写。\n"
                "- 优化目标：以降低 EXPLAIN JSON 中 query_block.cost_info.query_cost 为首要目标，且不改变结果集语义。\n"
                "- 优化策略：优先考虑索引使用与覆盖、谓词下推、调整连接顺序（基数驱动）、去除冗余子句/子查询、避免函数使索引失效、减少不必要的 DISTINCT/ORDER BY/FILESORT/TEMPORARY。\n"
                "- 兼容性与规范要求（严格遵循 Apache Calcite/ANSI SQL）：\n"
                "  1) 禁止使用方言特性：反引号`、LIMIT、非标准函数（如 IF、DATE_FORMAT、STR_TO_DATE 等）、Hint（如 /*+ ... */）、方言注释/语法；\n"
                "  2) 如需限制行数，请使用标准语法：OFFSET <n> ROWS FETCH FIRST <m> ROWS ONLY；\n"
                "  3) 标识符与关键字大小写：不得更改输入 SQL 中标识符的大小写；不要引入反引号；如必须引用标识符，仅使用 ANSI 的双引号；\n"
                "  4) 仅使用 ANSI 标准函数与语法；任何可能不被 Calcite 接受的写法，必须纠正为可解析的标准写法；\n"
                "  5) 输出必须是 Calcite 可解析的 SQL。\n"
                "\n"
                "【输出格式要求】\n"
                "请先给出结构化的“分析”部分，逐条说明你如何利用 EXPLAIN 与统计信息进行决策，至少包含：\n"
                "  - 来自 EXPLAIN 的证据（例如：using_filesort/using_temporary、rows/filtered/attached_condition、possible_keys/used_key/idx 覆盖、Join 类型、驱动表选择等）；\n"
                "  - 来自统计信息的证据（例如：表行数、索引存在性、列选择性/基数、外键/唯一约束等）；\n"
                "  - 每条改写的预期效果与其如何降低 query_cost（如提升过滤选择性、减少回表、避免临时表、移除排序、减少扫描范围等）。\n"
                "然后再输出优化后的 SQL 代码块，使用 ```sql ... ```。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始 SQL：\n```sql\n{sql}\n```\n\n"
                f"查询计划：\n{plan}\n\n"
                f"统计信息（JSON）：\n```json\n{stats}\n```\n\n"
                f"数据库 schema（DDL）：\n```sql\n{db_schema}\n```\n\n"
                "请给出语义等价且符合 Calcite/ANSI SQL 的优化版本（严格按上述输出格式）。"
            ),
        },
    ]
    try:
        llm = get_llm()
        content = llm.chat(messages)
        explanation = _extract_explanation_from_text(content)
        optimized_sql = _extract_sql_from_text(content)
        state["rewrite_explanation"] = explanation
        state["optimized_sql"] = optimized_sql
        # state.setdefault("history", []).append("[optimize_sql] 已生成候选改写 SQL与改写说明")
    except Exception as e:
        # state.setdefault("history", []).append(f"[optimize_sql] 生成候选改写失败：{str(e)}")
        pass
    return state

def llm_equivalence_check(sql1: str, sql2: str, db_schema: Optional[str] = None) -> Dict[str, Any]:
    logger.debug(f"call llm_equivalence_check")
    messages = [
        {
            "role": "system",
            "content": (
                "你是 SQL 语义等价性验证器。请基于给定的数据库 schema，判断两个 SQL 查询是否语义等价（返回的结果集在所有数据状态下相同）。\n"
                "- 必须从语义层面分析：连接、过滤、分组、聚合、去重、排序、NULL 处理、表达式等；不要仅凭格式或重命名。\n"
                "- 若存在不确定或依赖具体数据分布的情况，请谨慎处理，尽量避免误判为等价。\n"
                "- 仅返回 JSON：{\"equivalent\": true/false}，不要包含其他文本。"
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
        llm = get_llm()
        content = llm.chat(messages)
        import re, json
        m = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        json_str = m.group(1) if m else content
        result = json.loads(json_str)
        return {
            "success": True,
            "equivalent": bool(result.get("equivalent", False)),
        }
    except Exception as e:
        return {
            "success": False,
            "equivalent": False,
            "error": str(e),
        }

def final_report_node(state: Dict[str, Any]) -> Dict[str, Any]:
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
                "你是一名资深MySQL数据库性能优化专家。请根据提供的信息生成一份详细的SQL优化报告，比较不同优化方案的优缺点。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始SQL:\n```sql\n{sql}\n```\n\n"
                f"优化方案比较:\n{plans_info}\n\n"
                "请提供一份详细的优化报告，包括:\n"
                "1. 原始SQL的问题分析\n"
                "2. 各个优化方案的比较和成本对比\n\n"
                "请以Markdown格式返回报告。"
            ),
        },
    ]
    
    try:
        llm = get_llm()
        report = llm.chat(messages)
        state["final_report"] = report
        # state.setdefault("history", []).append("[report] 已生成最终优化报告")
    except Exception as e:
        state["final_report"] = f"生成报告失败: {str(e)}"
        # state.setdefault("history", []).append(f"[report] 生成报告失败: {str(e)}")
    
    return state


def generate_optimization_plans(state: Dict[str, Any]) -> Dict[str, Any]:
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
                "  5) 每个方案的 optimized_sql 字段必须是 Calcite 可解析的 SQL。\n"
                "- 输出要求：以JSON格式返回两种优化方案，每种方案包含方案ID、描述、优化后的SQL和“详细的优化理由”。\n"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原始 SQL：\n```sql\n{sql}\n```\n\n"
                f"数据库 schema（DDL）：\n```sql\n{db_schema}\n```\n\n"
                f"查询计划：\n{plan}\n\n"
                f"统计信息（JSON）：\n```json\n{stats}\n```\n\n"
                "请提供两种不同的优化方案，每种方案采用不同的优化思路。以JSON格式返回结果：\n"
                "```json\n"
                "{\n"
                '  "plans": [\n'
                "    {\n"
                '      "plan_id": "plan1",\n'
                '      "description": "方案1的简要描述",\n'
                '      "optimized_sql": "优化后的SQL1（严格符合 Calcite/ANSI SQL）",\n'
                '      "reasoning": "详细的优化理由（必须引用 EXPLAIN 与统计信息中的具体证据，并解释如何降低 query_cost）"\n'
                "    },\n"
                "    {\n"
                '      "plan_id": "plan2",\n'
                '      "description": "方案2的简要描述",\n'
                '      "optimized_sql": "优化后的SQL2（严格符合 Calcite/ANSI SQL）",\n'
                '      "reasoning": "详细的优化理由（必须引用 EXPLAIN 与统计信息中的具体证据，并解释如何降低 query_cost）"\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "```\n"
                "仅返回JSON格式的结果，不要包含其他解释。确保两种方案采用不同的优化思路，并且每个 optimized_sql 都满足 Calcite 语法。"
            ),
        },
    ]

    try:
        llm = get_llm()
        content = llm.chat(messages)
        
        # 提取JSON部分
        import re
        import json
        
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content
            
        result = json.loads(json_str)
        
        # 将生成的方案添加到状态中
        plans = []
        for plan_data in result.get("plans", []):
            plan = {
                "plan_id": plan_data.get("plan_id", ""),
                "description": plan_data.get("description", ""),
                "optimized_sql": plan_data.get("optimized_sql", ""),
                "reasoning": plan_data.get("reasoning", ""),
                "equivalence": False,
                "cost": None
            }
            plans.append(plan)
        
        state["optimization_plans"] = plans
        state["current_plan_index"] = 0
        
        if plans:
            state["optimized_sql"] = plans[0]["optimized_sql"]
        
        # state.setdefault("history", []).append(f"[generate_plans] 已生成 {len(plans)} 个优化方案")
        
    except Exception as e:
        # state.setdefault("history", []).append(f"[generate_plans] 生成优化方案失败: {str(e)}")
        pass
    
    return state