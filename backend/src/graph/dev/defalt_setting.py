from src.graph.state import SQLState
from src.config import get_settings
from src.llm import LangchainLLMClient
from src.utils.mysql_utils import MySQLUtils

def default_setting_node(state: SQLState) -> SQLState:
    state["llm"] = LangchainLLMClient.create_from_settings()
    state["mysql_utils"] = MySQLUtils.create_from_settings()
    return state