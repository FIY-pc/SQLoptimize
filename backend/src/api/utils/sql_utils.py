"""SQL工具函数，用于安全地添加分页限制"""
from typing import Optional


def add_pagination_to_sql(sql: str, page: int, page_size: int, database_type: Optional[str] = None) -> str:
    """
    在SQL语句上添加分页限制
    将用户SQL包装在子查询中，并在外层添加LIMIT和OFFSET。
    
    Args:
        sql: 原始SQL语句
        page: 页码（从1开始）
        page_size: 每页记录数
        database_type: 数据库类型（sqlite, mysql, postgresql等）
    
    Returns:
        添加了LIMIT和OFFSET的SQL语句
    """
    # 规范化SQL，去除首尾空白和末尾的分号
    sql = sql.strip().rstrip(';').strip()
    
    # 检测是否为SELECT查询（允许SELECT开头的查询，包括WITH语句）
    sql_upper = sql.upper().strip()
    is_select = sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
    
    if not is_select:
        raise ValueError("只允许执行SELECT查询语句")
    
    # 计算OFFSET
    offset = (page - 1) * page_size
    
    # 根据数据库类型选择LIMIT语法
    if database_type == 'mysql' or database_type == 'sqlite' or database_type is None:
        # MySQL和SQLite使用: LIMIT page_size OFFSET offset
        # 将原SQL包装在子查询中，确保无论原SQL是否已有LIMIT，都会应用我们的限制
        paginated_sql = f"SELECT * FROM ({sql}) AS wrapped_query LIMIT {page_size} OFFSET {offset}"
    elif database_type == 'postgresql':
        # PostgreSQL使用: LIMIT page_size OFFSET offset
        paginated_sql = f"SELECT * FROM ({sql}) AS wrapped_query LIMIT {page_size} OFFSET {offset}"
    else:
        # 默认使用标准SQL语法
        paginated_sql = f"SELECT * FROM ({sql}) AS wrapped_query LIMIT {page_size} OFFSET {offset}"
    
    return paginated_sql


def get_count_sql(sql: str) -> str:
    """
    生成用于统计总数的SQL语句。
    将原SQL包装在COUNT查询中。
    
    Args:
        sql: 原始SQL语句
    
    Returns:
        COUNT查询语句
    """
    # 规范化SQL，去除首尾空白和末尾的分号
    sql = sql.strip().rstrip(';').strip()
    # 将原SQL包装在子查询中，然后统计行数
    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) AS count_query"
    return count_sql

