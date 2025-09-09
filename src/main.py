import argparse
from rich.console import Console
from rich.panel import Panel

from .pipelines import execute_pipeline_cli

console = Console()

def run(sql: str) -> None:
    final_state = execute_pipeline_cli(sql)

    optimized = final_state.get("optimized_sql") or "(未生成)"
    plan = final_state.get("plan_feedback") or "(无计划反馈)"

    console.print(Panel.fit(optimized, title="优化后 SQL", border_style="green"))
    console.print(Panel.fit(plan, title="计划/分析反馈", border_style="cyan"))

    # 调试信息
    history = final_state.get("history", [])
    if history:
        console.print(Panel.fit("\n".join(history), title="历史轨迹", border_style="magenta"))


def main():
    parser = argparse.ArgumentParser(description="SQL 优化与计划检查（基于 LangGraph 与 qwen-plus）")
    parser.add_argument("sql", type=str, help="要优化的 SQL 语句（用引号括起来）")
    args = parser.parse_args()
    run(args.sql)


if __name__ == "__main__":
    main()