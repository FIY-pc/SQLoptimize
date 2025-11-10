from typing import Optional, Tuple, Dict, Any, AsyncGenerator
from src.graph.graph import build_sqlopt_graph
from src.graph.state import build_initial_state, InputState
from src.graph.state import SQLState as State
from src.utils import get_unix_timestamp
from src.llm.client import get_llm
from src.llm.client import LLMClientFactory
from src.utils.mysql_utils import MySQLUtils
from src.config import get_settings
from src.schemas.pipeline_message import create_error_message, create_end_message
import logging
from src.api.repository import DbSchemaRepository, ModelConnectionRepository, DatabaseConnectionRepository
from langchain_core.messages import AIMessageChunk
logger = logging.getLogger(__name__)

async def execute_pipeline_cli(sql: str, db_schema: Optional[str] = None) -> State:
    """
    供 CLI 用的执行函数
    """
    settings = get_settings()
    
    llm = get_llm()
    mysql_utils = MySQLUtils.create_from_settings()
    input_state = InputState(
        sql=sql, 
        db_schema=db_schema,
        llm=llm,
        mysql_utils=mysql_utils
    )

    app = build_sqlopt_graph()
    init_state = build_initial_state(input_state)
    final_state: State = await app.ainvoke(init_state)  # type: ignore
    return final_state

async def build_input_state(
    sql: str, 
    user_id: int = 0
) -> InputState:
    """
    构建输入状态
    """
    db_schema_repo = DbSchemaRepository()
    model_repo = ModelConnectionRepository()
    db_conn_repo = DatabaseConnectionRepository()

    active_db_schema = db_schema_repo.get_active_by_user_id(user_id)
    active_model = model_repo.get_active_by_user_id(user_id)
    active_db_conn = db_conn_repo.get_active_by_user_id(user_id)

    logger.debug(f"active_db_schema id: {active_db_schema.id}, schema_content: {active_db_schema.schema_content}")
    logger.debug(f"active_model id: {active_model.id}, model: {active_model.model}, enable_thinking: {active_model.enable_thinking}")
    logger.debug(f"active_db_conn id: {active_db_conn.id}, database_uri: {active_db_conn.database_uri}")
    
    llm = LLMClientFactory.create_llm_client(
        model=active_model.model,
        base_url=active_model.base_url,
        api_key=active_model.api_key,
        enable_thinking=active_model.enable_thinking
    )
    
    mysql_utils = MySQLUtils(
        database_url=active_db_conn.database_uri
    )

    input_state = InputState(
        sql=sql, 
        db_schema=active_db_schema.schema_content,
        database=active_db_conn.database(),
        llm=llm,
        mysql_utils=mysql_utils
    )
    return input_state

async def execute_pipeline_api(
    sql: str, 
    user_id: int = 0
) -> State:
    """
    供 API 用的执行函数
    """
    input_state = await build_input_state(sql, user_id)
    init_state = build_initial_state(input_state)

    app = build_sqlopt_graph()
    final_state: State = await app.ainvoke(init_state)
    return final_state

async def execute_pipeline_stream(
    sql: str, 
    user_id: int = 0
)->AsyncGenerator[Tuple[str, AIMessageChunk, Dict[str, Any]], None]:
    """
    供 API 用的流式执行函数
    """
    input_state = await build_input_state(sql, user_id)
    init_state = build_initial_state(input_state)

    app = build_sqlopt_graph()
    filter_nodes = ["get_stats","check_equivalence"]
    stream_mode = ["messages","custom"]
    try:
        async for mode, chunk in app.astream(init_state, stream_mode=stream_mode):
            mode = mode if mode else "unknown"
            message_chunk = chunk[0]
            metadata = chunk[1]
            if metadata.get("langgraph_node") in filter_nodes:
                continue
            yield mode, message_chunk, metadata
    except Exception as e:
        logger.error(f"Error in execute_pipeline_stream: {e}")
        # 发送错误消息
        error_message = create_error_message(str(e), get_unix_timestamp())
        yield "error", error_message, {"error": True}