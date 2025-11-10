from src.graph.state import SQLState
from src.config import get_settings
from src.llm.client import LLMClientFactory
from src.utils.mysql_utils import MySQLUtils

def default_setting_node(state: SQLState) -> SQLState:
    settings = get_settings()
    state["llm"] = LLMClientFactory.create_from_settings()
    state["mysql_utils"] = MySQLUtils.create_from_settings()
    
    # 如果state中没有database，就使用默认的mysql_database
    state["database"] = state.get("database") or settings.mysql_database

    return state