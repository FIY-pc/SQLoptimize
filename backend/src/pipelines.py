from typing import Optional
from src.graph.graph import build_sqlopt_graph
from src.graph.state import build_initial_state, InputState
from src.graph.state import SQLState as State
from src.utils import get_unix_timestamp
from src.llm.client import get_llm
from src.utils.mysql_utils import MySQLUtils
from src.config import get_settings
from src.schemas.pipeline_message import create_error_message, create_end_message
import logging
import sqlite3
logger = logging.getLogger(__name__)

# 供 CLI 用的执行函数
async def execute_pipeline_cli(sql: str, db_schema: Optional[str] = None) -> State:
    settings = get_settings()
    
    llm = get_llm()
    mysql_utils = MySQLUtils.create_from_settings()
    fallback_sqlite = sqlite3.connect(settings.db_path)
    input_state = InputState(
        sql=sql, 
        db_schema=db_schema,
        llm=llm,
        mysql_utils=mysql_utils,
        fallback_sqlite=fallback_sqlite
    )

    app = build_sqlopt_graph()
    init_state = build_initial_state(input_state)
    final_state: State = await app.ainvoke(init_state)  # type: ignore
    return final_state

# 供 API 用的执行函数
async def execute_pipeline_api(sql: str, db_schema: Optional[str] = None) -> State:
    settings = get_settings()
    llm = get_llm()
    mysql_utils = MySQLUtils.create_from_settings()
    fallback_sqlite = sqlite3.connect(settings.db_path)
    input_state = InputState(
        sql=sql, 
        db_schema=db_schema,
        llm=llm,
        mysql_utils=mysql_utils,
        fallback_sqlite=fallback_sqlite
    )

    app = build_sqlopt_graph()
    init_state = build_initial_state(input_state)
    final_state: State = await app.ainvoke(init_state)  # type: ignore
    return final_state

# 流式输出版执行函数
async def execute_pipeline_stream(
    sql: str, 
    db_schema: Optional[str] = None
):
    settings = get_settings()
    llm = get_llm()
    mysql_utils = MySQLUtils.create_from_settings()
    fallback_sqlite = sqlite3.connect(settings.db_path)
    input_state = InputState(
        sql=sql, 
        db_schema=db_schema,
        llm=llm,
        mysql_utils=mysql_utils,
        fallback_sqlite=fallback_sqlite
    )

    app = build_sqlopt_graph()
    init_state = build_initial_state(input_state)
    try:
        async for message_chunk, metadata in app.astream(init_state, stream_mode="messages"):
            yield message_chunk, metadata
    except Exception as e:
        logger.error(f"Error in execute_pipeline_stream: {e}")
        # 发送错误消息
        error_message = create_error_message(str(e), get_unix_timestamp())
        yield error_message, {"error": True}
    finally:
        # 发送结束标记
        end_message = create_end_message("completed", get_unix_timestamp())
        yield end_message, {"end": True}
    