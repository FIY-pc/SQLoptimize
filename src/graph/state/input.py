from typing import TypedDict, Optional
from src.llm import LLMClient
from src.utils.mysql_utils import MySQLUtils
import sqlite3


class InputState(TypedDict, total=False):
    sql: str
    db_schema: Optional[str]
    max_iterations: int
    llm: LLMClient
    mysql_utils: MySQLUtils
    fallback_sqlite: Optional[sqlite3.Connection]