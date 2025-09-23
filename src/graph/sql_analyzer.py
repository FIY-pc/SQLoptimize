"""SQL分析模块，提供SQL解析、表列提取、统计信息收集等功能"""

import re
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass

from src.utils.mysql_utils import MySQLUtils
from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """表信息数据类"""
    name: str
    alias: Optional[str] = None
    database: Optional[str] = None


@dataclass
class ColumnInfo:
    """列信息数据类"""
    name: str
    table: Optional[str] = None
    alias: Optional[str] = None


@dataclass
class SQLAnalysisResult:
    """SQL分析结果"""
    tables: List[TableInfo]
    columns: List[ColumnInfo]
    join_conditions: List[str]
    where_conditions: List[str]
    order_by_columns: List[str]
    group_by_columns: List[str]
    query_type: str  # SELECT, INSERT, UPDATE, DELETE


class SQLAnalyzer():
    """SQL分析器"""

    def __init__(self):
        self.table_pattern = re.compile(
            r'\b(?:FROM|JOIN|UPDATE|INTO)\s+(?:(?P<db>\w+)\.)?(?P<table>\w+)(?:\s+(?:AS\s+)?(?P<alias>\w+))?\b',
            re.IGNORECASE
        )
        self.column_pattern = re.compile(
            r'\b(?:(?P<table>\w+)\.)?(?P<column>\w+)\b'
        )

    def analyze_sql(self, sql: str) -> SQLAnalysisResult:
        """分析SQL语句，提取表、列、条件等信息"""
        sql = sql.strip()
        if not sql:
            return SQLAnalysisResult([], [], [], [], [], [], "UNKNOWN")

        # 确定查询类型
        query_type = self._get_query_type(sql)

        # 提取表信息
        tables = self._extract_tables(sql)

        # 提取列信息
        columns = self._extract_columns(sql, tables)

        # 提取各种条件
        join_conditions = self._extract_join_conditions(sql)
        where_conditions = self._extract_where_conditions(sql)
        order_by_columns = self._extract_order_by(sql)
        group_by_columns = self._extract_group_by(sql)

        return SQLAnalysisResult(
            tables=tables,
            columns=columns,
            join_conditions=join_conditions,
            where_conditions=where_conditions,
            order_by_columns=order_by_columns,
            group_by_columns=group_by_columns,
            query_type=query_type
        )

    def _get_query_type(self, sql: str) -> str:
        """获取SQL查询类型"""
        sql_upper = sql.upper().strip()
        if sql_upper.startswith('SELECT'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        elif sql_upper.startswith('WITH'):
            return 'SELECT'  # CTE通常是SELECT
        else:
            return 'UNKNOWN'

    def _extract_tables(self, sql: str) -> List[TableInfo]:
        """提取SQL中的表信息"""
        tables = []
        matches = self.table_pattern.finditer(sql)

        for match in matches:
            table_name = match.group('table')
            alias = match.group('alias')
            database = match.group('db')

            if table_name:
                tables.append(TableInfo(
                    name=table_name,
                    alias=alias,
                    database=database
                ))

        # 去重
        unique_tables = []
        seen = set()
        for table in tables:
            key = (table.name, table.alias, table.database)
            if key not in seen:
                seen.add(key)
                unique_tables.append(table)

        return unique_tables

    def _extract_columns(self, sql: str, tables: List[TableInfo]) -> List[ColumnInfo]:
        """提取SQL中的列信息"""
        columns = []

        # 创建表名到别名的映射
        table_aliases = {}
        for table in tables:
            if table.alias:
                table_aliases[table.alias] = table.name
            table_aliases[table.name] = table.name

        # 简化的列提取（实际应该使用SQL解析器）
        # 这里用正则表达式作为临时方案
        select_part = self._extract_select_part(sql)
        if select_part:
            column_matches = re.finditer(
                r'\b(?:(?P<table_ref>\w+)\.)?(?P<column>\w+)\b',
                select_part
            )

            for match in column_matches:
                column_name = match.group('column')
                table_ref = match.group('table_ref')

                # 跳过SQL关键字
                if column_name.upper() in ['SELECT', 'FROM', 'WHERE', 'AS', 'AND', 'OR', 'ORDER', 'BY', 'GROUP', 'HAVING']:
                    continue

                # 解析表引用
                table_name = None
                if table_ref:
                    table_name = table_aliases.get(table_ref, table_ref)

                columns.append(ColumnInfo(
                    name=column_name,
                    table=table_name
                ))

        return columns

    def _extract_select_part(self, sql: str) -> Optional[str]:
        """提取SELECT部分"""
        match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else None

    def _extract_join_conditions(self, sql: str) -> List[str]:
        """提取JOIN条件"""
        conditions = []
        join_matches = re.finditer(
            r'JOIN\s+\w+(?:\s+\w+)?\s+ON\s+(.*?)(?=\s+(?:JOIN|WHERE|GROUP|ORDER|$))',
            sql, re.IGNORECASE
        )

        for match in join_matches:
            condition = match.group(1).strip()
            if condition:
                conditions.append(condition)

        return conditions

    def _extract_where_conditions(self, sql: str) -> List[str]:
        """提取WHERE条件"""
        match = re.search(
            r'WHERE\s+(.*?)(?=\s+(?:GROUP|ORDER|LIMIT|$))',
            sql, re.IGNORECASE | re.DOTALL
        )

        if match:
            where_clause = match.group(1).strip()
            # 简单分割条件（实际应该使用SQL解析器）
            conditions = re.split(r'\s+(?:AND|OR)\s+', where_clause, flags=re.IGNORECASE)
            return [cond.strip() for cond in conditions if cond.strip()]

        return []

    def _extract_order_by(self, sql: str) -> List[str]:
        """提取ORDER BY列"""
        match = re.search(
            r'ORDER\s+BY\s+(.*?)(?=\s+(?:LIMIT|$))',
            sql, re.IGNORECASE | re.DOTALL
        )

        if match:
            order_clause = match.group(1).strip()
            columns = [col.strip() for col in order_clause.split(',')]
            return columns

        return []

    def _extract_group_by(self, sql: str) -> List[str]:
        """提取GROUP BY列"""
        match = re.search(
            r'GROUP\s+BY\s+(.*?)(?=\s+(?:HAVING|ORDER|LIMIT|$))',
            sql, re.IGNORECASE | re.DOTALL
        )

        if match:
            group_clause = match.group(1).strip()
            columns = [col.strip() for col in group_clause.split(',')]
            return columns

        return []


class StatisticsCollector:
    """统计信息收集器"""

    def __init__(self,database_url:str):
        self.analyzer = SQLAnalyzer()
        self.mysql_utils = MySQLUtils(database_url)
    
    def create_from_settings(self):
        settings = get_settings()
        database_url = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password or ''}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database or ''}"
        return self(database_url)

    def collect_table_statistics(self, sql: str, database: Optional[str] = None) -> Dict[str, Any]:
        """收集SQL涉及表的统计信息"""
        try:
            # 分析SQL
            analysis = self.analyzer.analyze_sql(sql)

            statistics = {
                "sql_analysis": {
                    "query_type": analysis.query_type,
                    "table_count": len(analysis.tables),
                    "column_count": len(analysis.columns),
                    "join_count": len(analysis.join_conditions),
                    "where_conditions": analysis.where_conditions,
                    "tables": [{"name": t.name, "alias": t.alias} for t in analysis.tables],
                    "columns": [{"name": c.name, "table": c.table} for c in analysis.columns]
                },
                "table_statistics": {},
                "collection_success": True,
                "collection_errors": []
            }

            # 收集每个表的统计信息
            for table in analysis.tables:
                try:
                    table_stats = self.mysql_utils.get_mysql_table_statistics(table.name, database)
                    if table_stats["success"]:
                        statistics["table_statistics"][table.name] = table_stats["statistics"]
                    else:
                        statistics["collection_errors"].append(
                            f"获取表 {table.name} 统计信息失败: {table_stats.get('error', '未知错误')}"
                        )
                except Exception as e:
                    error_msg = f"收集表 {table.name} 统计信息异常: {e}"
                    statistics["collection_errors"].append(error_msg)
                    logger.error(error_msg)

            if statistics["collection_errors"]:
                statistics["collection_success"] = False

            return statistics

        except Exception as e:
            logger.error(f"统计信息收集失败: {e}")
            return {
                "sql_analysis": None,
                "table_statistics": {},
                "collection_success": False,
                "collection_errors": [f"统计信息收集异常: {e}"]
            }

    def analyze_performance_bottlenecks(self, sql: str, execution_plan: Dict, statistics: Dict) -> Dict[str, Any]:
        """分析性能瓶颈"""
        bottlenecks = {
            "potential_issues": [],
            "recommendations": [],
            "severity": "LOW"  # LOW, MEDIUM, HIGH
        }

        analysis = statistics.get("sql_analysis", {})
        table_stats = statistics.get("table_statistics", {})

        # 分析大表扫描
        for table_name, stats in table_stats.items():
            table_info = stats.get("table_info", {})
            table_rows = table_info.get("TABLE_ROWS", 0)

            if table_rows and table_rows > 1000000:  # 超过100万行
                bottlenecks["potential_issues"].append(f"大表扫描: {table_name} ({table_rows:,} 行)")
                bottlenecks["recommendations"].append(f"考虑为表 {table_name} 添加适当的索引")
                bottlenecks["severity"] = "HIGH"

        # 分析缺失索引
        where_conditions = analysis.get("where_conditions", [])
        for condition in where_conditions:
            # 简单的条件分析（实际需要更复杂的解析）
            if any(op in condition for op in ['=', '>', '<', 'LIKE']):
                bottlenecks["recommendations"].append(f"检查条件 '{condition}' 是否有合适的索引")

        # 分析JOIN条件
        join_count = analysis.get("join_count", 0)
        if join_count > 3:
            bottlenecks["potential_issues"].append(f"复杂JOIN: {join_count} 个表连接")
            bottlenecks["recommendations"].append("考虑优化JOIN顺序和条件")
            if bottlenecks["severity"] == "LOW":
                bottlenecks["severity"] = "MEDIUM"

        return bottlenecks


def format_statistics_for_llm(statistics: Dict[str, Any]) -> str:
    """格式化统计信息供LLM使用"""
    if not statistics.get("collection_success"):
        return "统计信息收集失败: " + "; ".join(statistics.get("collection_errors", []))

    analysis = statistics.get("sql_analysis", {})
    table_stats = statistics.get("table_statistics", {})

    output = []

    # SQL分析信息
    output.append("=== SQL分析结果 ===")
    output.append(f"查询类型: {analysis.get('query_type', 'UNKNOWN')}")
    output.append(f"涉及表数: {analysis.get('table_count', 0)}")
    output.append(f"涉及列数: {analysis.get('column_count', 0)}")
    output.append(f"JOIN数量: {analysis.get('join_count', 0)}")

    # 表信息
    tables = analysis.get("tables", [])
    if tables:
        output.append("\n涉及的表:")
        for table in tables:
            alias_info = f" (别名: {table['alias']})" if table['alias'] else ""
            output.append(f"  - {table['name']}{alias_info}")

    # WHERE条件
    where_conditions = analysis.get("where_conditions", [])
    if where_conditions:
        output.append("\nWHERE条件:")
        for condition in where_conditions:
            output.append(f"  - {condition}")

    # 表统计信息
    output.append("\n=== 表统计信息 ===")
    for table_name, stats in table_stats.items():
        table_info = stats.get("table_info", {})
        indexes = stats.get("indexes", [])

        output.append(f"\n表: {table_name}")
        output.append(f"  行数: {table_info.get('TABLE_ROWS', 'Unknown'):,}")
        output.append(f"  数据大小: {table_info.get('DATA_LENGTH', 0) / 1024 / 1024:.2f} MB")
        output.append(f"  索引大小: {table_info.get('INDEX_LENGTH', 0) / 1024 / 1024:.2f} MB")

        # 索引信息
        if indexes:
            output.append("  索引:")
            index_groups = {}
            for idx in indexes:
                idx_name = idx['INDEX_NAME']
                if idx_name not in index_groups:
                    index_groups[idx_name] = []
                index_groups[idx_name].append(idx['COLUMN_NAME'])

            for idx_name, columns in index_groups.items():
                idx_type = "PRIMARY" if idx_name == "PRIMARY" else "INDEX"
                output.append(f"    - {idx_name} ({idx_type}): {', '.join(columns)}")

    return "\n".join(output)


# 主要导出函数
def analyze_sql_with_statistics(sql: str, database: Optional[str] = None) -> Tuple[SQLAnalysisResult, Dict[str, Any]]:
    """分析SQL并收集统计信息"""
    analyzer = SQLAnalyzer()
    collector = StatisticsCollector.create_from_settings()

    # SQL分析
    analysis = analyzer.analyze_sql(sql)

    # 统计信息收集
    statistics = collector.collect_table_statistics(sql, database)

    return analysis, statistics