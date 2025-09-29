import argparse
import asyncio
from rich.console import Console
from rich.panel import Panel
from typing import Optional
from src.pipelines import execute_pipeline_cli
import sys

console = Console()

def run(sql: str, db_schema: Optional[str] = None) -> None:
    final_state = asyncio.run(execute_pipeline_cli(sql, db_schema))

    # 引入 json 以格式化统计信息
    import json

    # 查询计划（改写前）
    plan_text = (
        final_state.get("plan")
        or final_state.get("plan_feedback")
        or "(无计划反馈)"
    )
    console.print(Panel.fit(plan_text, title="查询计划（改写前）", border_style="cyan"))

    # 数据库统计信息
    stats = final_state.get("stats") or {}
    stats_text = json.dumps(stats, ensure_ascii=False, indent=2, default=str)
    console.print(Panel.fit(stats_text, title="数据库统计信息", border_style="yellow"))

    # 优化后 SQL
    optimized = final_state.get("optimized_sql") or "(未生成)"
    console.print(Panel.fit(optimized, title="优化后 SQL", border_style="green"))

    # 等价性比较结果
    equivalence = bool(final_state.get("equivalence", False))
    equivalence_text = "✔ 等价" if equivalence else "✘ 不等价"
    console.print(Panel.fit(equivalence_text, title="等价性校验结果", border_style=("green" if equivalence else "red")))

    # 成本估算对比
    cost_before = final_state.get("cost_before")
    cost_after = final_state.get("cost_after")
    lines = [
        f"改写前: {cost_before if cost_before is not None else 'N/A'}",
        f"改写后: {cost_after if cost_after is not None else 'N/A'}",
    ]
    if isinstance(cost_before, (int, float)) and isinstance(cost_after, (int, float)) and cost_before > 0:
        improvement = (cost_before - cost_after) / cost_before * 100.0
        lines.append(f"改善比例: {improvement:.2f}%")
    console.print(Panel.fit("\n".join(lines), title="成本估算对比（改写前 vs 改写后）", border_style="blue"))

    # 调试信息：历史轨迹
    history = final_state.get("history", [])
    if history:
        console.print(Panel.fit("\n".join(history), title="历史轨迹", border_style="magenta"))


def main():
    parser = argparse.ArgumentParser(description="SQL 优化与计划检查（基于 LangGraph 与 qwen-plus）")
    parser.add_argument("sql", type=str, nargs="?", default="", help="要优化的 SQL 语句（字符串，可选；若使用 --sql_file 则不必提供）")
    parser.add_argument("--db_schema", type=str, required=False, default="", help="数据库 schema（字符串，可选）")
    
    #从文件读取 SQL 与 schema
    parser.add_argument("--sql_file", type=str, required=False, default="", help="包含 SQL 的文件路径（UTF-8/UTF-8-SIG）")
    parser.add_argument("--db_schema_file", type=str, required=False, default="", help="包含数据库 schema 的文件路径（UTF-8/UTF-8-SIG）")
    args = parser.parse_args()

    # 若提供了 SQL 文件，则读取文件内容覆盖 sql
    if args.sql_file:
        try:
            with open(args.sql_file, "r", encoding="utf-8-sig") as f:
                file_sql = f.read().strip()
            args.sql = file_sql
        except Exception as e:
            console.print(Panel.fit(f"读取 SQL 文件失败：{e}", title="错误", border_style="red"))
            sys.exit(2)

    # 若未提供字符串 sql，也未提供 sql_file，则报错退出
    if not args.sql:
        console.print(Panel.fit("请提供 SQL或使用 --sql_file 指定 SQL 文件", title="错误", border_style="red"))
        sys.exit(2)

    # 若未直接传入 db_schema，但提供了 schema 文件，则读取文件内容
    if not args.db_schema and args.db_schema_file:
        try:
            with open(args.db_schema_file, "r", encoding="utf-8-sig") as f:
                file_schema = f.read()
            args.db_schema = file_schema
        except Exception as e:
            console.print(Panel.fit(f"读取 schema 文件失败：{e}", title="错误", border_style="red"))
            sys.exit(2)

    run(args.sql, args.db_schema)


if __name__ == "__main__":
    main()