import json
from pathlib import Path
from typing import Optional, Any, Sequence
from src.stream.stream_writer import StreamWriter
import logging
from .state import State
from .graph import build_graph

# 构建初始状态，从项目根目录读取 rules.json
def build_init_state(
    sql: str, 
    stream_writer: StreamWriter,
    db_schema: Optional[str] = None
) -> State:
    init_state: State = {
        "input_sql": sql, 
        "history": [], 
        "stream_writer": stream_writer, 
        "db_schema": db_schema
    }

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
        init_state["history"].append(f"[main] 读取 rules.json 失败：{e}")
    return init_state

# 供 CLI 用的执行函数，同步版本
def execute_pipeline_cli(sql: str, db_schema: Optional[str] = None) -> State:
    app = build_graph()
    init_state = build_init_state(sql=sql, db_schema=db_schema)
    final_state: State = app.invoke(init_state)  # type: ignore
    return final_state

# 供 API 用的执行函数，异步版本
async def execute_pipeline_api(sql: str, db_schema: Optional[str] = None) -> State:
    app = build_graph()
    init_state = build_init_state(sql=sql, db_schema=db_schema)
    final_state: State = await app.ainvoke(init_state)  # type: ignore
    return final_state

# 流式输出版执行函数
async def execute_pipeline_stream(
    sql: str, 
    stream_writer: StreamWriter,
    db_schema: Optional[str] = None
):
    app = build_graph()
    init_state = build_init_state(
        sql=sql, 
        stream_writer=stream_writer,
        db_schema=db_schema
    )
    async for chunk in app.astream(input=init_state):
        yield chunk