import argparse
from rich.console import Console
from rich.panel import Panel

from .graph import build_graph
from .state import State
import json
from pathlib import Path

console = Console()


def run(sql: str) -> None:
    app = build_graph()
    init_state: State = {"input_sql": sql}
    # 确保有 history，便于在加载规则时记录日志
    if "history" not in init_state:
        init_state["history"] = []

    # 自动从项目根目录加载 rules.json（若存在则注入到状态）
    try:
        root = Path(__file__).resolve().parents[1]
        rules_file = root / "rules.json"
        if rules_file.is_file():
            try:
                # 使用 utf-8-sig 自动忽略 BOM
                with rules_file.open("r", encoding="utf-8-sig") as f:
                    rules = json.load(f)
            except Exception:
                # 移除可能的 U+FEFF 再解析
                with rules_file.open("r", encoding="utf-8") as f:
                    txt = f.read().lstrip("\ufeff")
                    rules = json.loads(txt)
            if isinstance(rules, dict):
                init_state["rewrite_rules"] = rules
                # 记录已加载的规则条数
                try:
                    count = len(rules.get("rules", [])) if isinstance(rules.get("rules", None), list) else 0
                except Exception:
                    count = 0
                init_state["history"].append(f"[main] 已加载自定义改写规则：{count} 条")
            else:
                init_state["history"].append("[main] rules.json 顶层不是对象（dict），已忽略")
        else:
            init_state["history"].append("[main] 未发现 rules.json（将不注入自定义改写规则）")
    except Exception as e:
        # 读取失败时记录错误，便于排查
        init_state["history"].append(f"[main] 读取 rules.json 失败：{e}")
    except Exception:
        # 读取失败时忽略，不影响无规则运行
        pass

    final_state: State = app.invoke(init_state)  # type: ignore

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