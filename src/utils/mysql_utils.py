"""MySQL数据库工具模块，提供连接、执行计划抓取和统计信息收集功能"""

import pymysql
from typing import Dict, List, Optional, Any, Tuple
import logging
from contextlib import contextmanager
from sqlalchemy import text
from src.config import get_settings
from src.db.registry import DatabaseRegistry

logger = logging.getLogger(__name__)


class MySQLUtils(DatabaseRegistry):
    def __init__(self, database_url: Optional[str] = None):
        self.settings = get_settings()
        # 只初始化同步连接，不初始化异步连接
        self._database_type = None
        self._database_url = database_url
        self._engine = None
        self._session_factory = None
        self._initialized = {"sync": False, "async": False}
        self.logger = logging.getLogger(__name__)
        
        # 手动设置数据库类型和初始化同步连接
        if database_url:
            self._detect_database_type(database_url)
        else:
            self.database_type = 'mysql'
        
        if self.database_type != 'mysql':
            raise ValueError("MySQLUtils只能用于MySQL数据库")
        
        # 只初始化同步连接
        self.initialize_sync()

    @classmethod
    def create_from_settings(cls) -> 'MySQLUtils':
        """从配置设置创建MySQLUtils实例"""
        settings = get_settings()
        database_url = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password or ''}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database or ''}"
        return cls(database_url)

    def get_mysql_explain_plan(self, sql: str, database: Optional[str] = None) -> Dict[str, Any]:
        """获取MySQL执行计划"""
        try:
            with self.session() as session:
                # 切换到指定数据库
                if database:
                    session.execute(text(f"USE `{database}`"))

                # 获取JSON格式的执行计划
                explain_json_sql = text(f"EXPLAIN FORMAT=JSON {sql}")
                explain_json_result = session.execute(explain_json_sql).fetchone()

                # 获取传统格式的执行计划作为备用
                explain_traditional_sql = text(f"EXPLAIN {sql}")
                explain_traditional_result = session.execute(explain_traditional_sql).fetchall()

                return {
                    "success": True,
                    "explain_json": explain_json_result[0] if explain_json_result else None,
                    "explain_traditional": [dict(row._mapping) for row in explain_traditional_result],
                    "sql": sql
                }

        except Exception as e:
            logger.error(f"获取MySQL执行计划失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "sql": sql
            }


    def get_mysql_table_statistics(self, table_name: str, database: Optional[str] = None) -> Dict[str, Any]:
        """获取MySQL表统计信息"""
        try:
            with self.session() as session:
                # 切换到指定数据库
                if database:
                    session.execute(text(f"USE `{database}`"))
                    db_name = database
                else:
                    result = session.execute(text("SELECT DATABASE()")).fetchone()
                    db_name = result[0] if result else None

                if not db_name:
                    raise ValueError("无法确定数据库名称")

                statistics = {}

                # 1. 表基本信息
                table_info_sql = text("""
                    SELECT TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, AUTO_INCREMENT,
                        CREATE_TIME, UPDATE_TIME, TABLE_COLLATION
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name
                """)
                table_info_result = session.execute(table_info_sql, {"db_name": db_name, "table_name": table_name}).fetchone()
                statistics['table_info'] = dict(table_info_result._mapping) if table_info_result else None

                # 2. 列信息
                columns_sql = text("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                        CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """)
                columns_result = session.execute(columns_sql, {"db_name": db_name, "table_name": table_name}).fetchall()
                statistics['columns'] = [dict(row._mapping) for row in columns_result]

                # 3. 索引信息
                indexes_sql = text("""
                    SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, NON_UNIQUE,
                        INDEX_TYPE, CARDINALITY, SUB_PART, NULLABLE
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """)
                indexes_result = session.execute(indexes_sql, {"db_name": db_name, "table_name": table_name}).fetchall()
                statistics['indexes'] = [dict(row._mapping) for row in indexes_result]

                # 4. 外键与约束信息（用于标识外键列）
                key_usage_sql = text("""
                    SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME, CONSTRAINT_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = :db_name AND TABLE_NAME = :table_name
                """)
                key_usage_result = session.execute(key_usage_sql, {"db_name": db_name, "table_name": table_name}).fetchall()
                key_usage_rows = [dict(row._mapping) for row in key_usage_result]

                # 5. 组装列级统计（与用户示例字段一致）
                #    - 主键：索引 INDEX_NAME='PRIMARY' 的列视为主键
                #    - 外键：KEY_COLUMN_USAGE 中 REFERENCED_TABLE_NAME 非空的列视为外键
                #    - 索引：STATISTICS 中存在记录的列视为有索引；优先展示 PRIMARY / UNIQUE，其次 NORMAL
                pk_columns = set(
                    row["COLUMN_NAME"] for row in statistics['indexes']
                    if isinstance(row, dict) and str(row.get("INDEX_NAME", "")).upper() == "PRIMARY"
                )
                fk_columns = set(
                    row["COLUMN_NAME"] for row in key_usage_rows
                    if row.get("REFERENCED_TABLE_NAME")
                )

                # 为每个列找一个“代表性索引”（PRIMARY 优先，其次 UNIQUE，再普通）
                # 构建 column -> [index rows]
                from collections import defaultdict
                col_to_indexes = defaultdict(list)
                for row in statistics['indexes']:
                    if isinstance(row, dict):
                        col_to_indexes[row.get("COLUMN_NAME")].append(row)

                def pick_representative_index(col_name: str) -> Optional[Dict[str, Any]]:
                    idxs = col_to_indexes.get(col_name, [])
                    if not idxs:
                        return None
                    # PRIMARY 优先
                    for r in idxs:
                        if str(r.get("INDEX_NAME", "")).upper() == "PRIMARY":
                            return r
                    # UNIQUE 次之（NON_UNIQUE == 0）
                    for r in idxs:
                        if int(r.get("NON_UNIQUE", 1)) == 0:
                            return r
                    # 其余任选第一个
                    return idxs[0]

                column_stats = []
                for col in statistics['columns']:
                    col_name = col.get("COLUMN_NAME")
                    rep_idx = pick_representative_index(col_name)
                    has_index = "Y" if rep_idx is not None else "N"
                    index_name = (rep_idx.get("INDEX_NAME") if rep_idx else None)
                    index_type = None
                    seq_in_index = None
                    if rep_idx:
                        index_type = "UNIQUE" if int(rep_idx.get("NON_UNIQUE", 1)) == 0 else "NORMAL"
                        seq_in_index = rep_idx.get("SEQ_IN_INDEX")
                    
                    # 添加列的统计信息：distinct值、最大值、最小值
                    distinct_count = None
                    min_value = None
                    max_value = None
                    try:
                        safe_col_name = col_name.replace('`', '``')
                        
                        # 获取distinct值数量
                        distinct_sql = text(f"SELECT COUNT(DISTINCT `{safe_col_name}`) FROM `{table_name}`")
                        distinct_result = session.execute(distinct_sql).fetchone()
                        distinct_count = distinct_result[0] if distinct_result else None
                        
                        # 获取最小值和最大值
                        minmax_sql = text(f"SELECT MIN(`{safe_col_name}`), MAX(`{safe_col_name}`) FROM `{table_name}`")
                        minmax_result = session.execute(minmax_sql).fetchone()
                        if minmax_result:
                            min_value = minmax_result[0]
                            max_value = minmax_result[1]
                    except Exception as e:
                        logger.warning(f"获取列 {col_name} 的统计信息失败: {e}")

                    # 对齐用户示例的字段命名
                    column_stats.append({
                        "TABLE_NAME": table_name,
                        "COLUMN_NAME": col_name,
                        "DATA_TYPE": col.get("DATA_TYPE"),
                        "DATA_LENGTH": col.get("CHARACTER_MAXIMUM_LENGTH"),
                        "NUMERIC_PRECISION": col.get("NUMERIC_PRECISION"),
                        "NUMERIC_SCALE": col.get("NUMERIC_SCALE"),
                        "IS_PRIMARY_KEY": "Y" if col_name in pk_columns else "N",
                        "IS_FOREIGN_KEY": "Y" if col_name in fk_columns else "N",
                        "HAS_INDEX": has_index,
                        "INDEX_NAME": index_name,
                        "INDEX_TYPE": index_type,
                        "SEQ_IN_INDEX": seq_in_index,
                        "DISTINCT_COUNT": distinct_count,
                        "MIN_VALUE": min_value,
                        "MAX_VALUE": max_value,
                    })

                statistics["column_stats"] = column_stats

                return {
                    "success": True,
                    "table_name": table_name,
                    "database": db_name,
                    "statistics": statistics
                }

        except Exception as e:
            logger.error(f"获取表统计信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "table_name": table_name,
                "database": database
            }


    def get_database_schemas(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """获取数据库schema信息"""
        try:
            with self.session() as session:
                # 获取数据库列表
                if pattern:
                    databases_sql = text("SHOW DATABASES LIKE :pattern")
                    result = session.execute(databases_sql, {"pattern": pattern}).fetchall()
                else:
                    databases_sql = text("SHOW DATABASES")
                    result = session.execute(databases_sql).fetchall()

                databases = [row[0] for row in result]

                return {
                    "success": True,
                    "databases": databases
                }

        except Exception as e:
            logger.error(f"获取数据库schema失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


    def get_tpch_tables_info(self, database: str = "tpch_1g") -> Dict[str, Any]:
        """获取TPCH基准测试数据集的表信息"""
        try:
            with self.session() as session:
                # 切换到TPCH数据库
                session.execute(text(f"USE `{database}`"))

                # 获取所有表
                tables_result = session.execute(text("SHOW TABLES")).fetchall()
                tables = [row[0] for row in tables_result]

                tpch_info = {
                    "database": database,
                    "tables": {}
                }

                # 获取每个表的详细信息
                for table in tables:
                    table_stats = self.get_mysql_table_statistics(table, database)
                    if table_stats["success"]:
                        tpch_info["tables"][table] = table_stats["statistics"]

                return {
                    "success": True,
                    "tpch_info": tpch_info
                }

        except Exception as e:
            logger.error(f"获取TPCH表信息失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "database": database
            }


    def test_mysql_connection(self) -> Dict[str, Any]:
        """测试MySQL连接"""
        try:
            with self.session() as session:
                version_result = session.execute(text("SELECT VERSION() as version")).fetchone()
                db_result = session.execute(text("SELECT DATABASE() as current_db")).fetchone()

                return {
                    "success": True,
                    "version": version_result[0] if version_result else "Unknown",
                    "current_database": db_result[0] if db_result else None
                }

        except Exception as e:
            logger.error(f"MySQL连接测试失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


    # TPCH标准schema定义
    TPCH_SCHEMA = {
        "customer": {
            "columns": ["c_custkey", "c_name", "c_address", "c_nationkey", "c_phone", "c_acctbal", "c_mktsegment", "c_comment"],
            "primary_key": ["c_custkey"],
            "foreign_keys": [("c_nationkey", "nation.n_nationkey")]
        },
        "lineitem": {
            "columns": ["l_orderkey", "l_partkey", "l_suppkey", "l_linenumber", "l_quantity", "l_extendedprice",
                    "l_discount", "l_tax", "l_returnflag", "l_linestatus", "l_shipdate", "l_commitdate",
                    "l_receiptdate", "l_shipinstruct", "l_shipmode", "l_comment"],
            "primary_key": ["l_orderkey", "l_linenumber"],
            "foreign_keys": [
                ("l_orderkey", "orders.o_orderkey"),
                ("l_partkey", "part.p_partkey"),
                ("l_suppkey", "supplier.s_suppkey"),
                (("l_partkey", "l_suppkey"), "partsupp.ps_partkey")
            ]
        },
        "nation": {
            "columns": ["n_nationkey", "n_name", "n_regionkey", "n_comment"],
            "primary_key": ["n_nationkey"],
            "foreign_keys": [("n_regionkey", "region.r_regionkey")]
        },
        "orders": {
            "columns": ["o_orderkey", "o_custkey", "o_orderstatus", "o_totalprice", "o_orderdate",
                    "o_orderpriority", "o_clerk", "o_shippriority", "o_comment"],
            "primary_key": ["o_orderkey"],
            "foreign_keys": [("o_custkey", "customer.c_custkey")]
        },
        "part": {
            "columns": ["p_partkey", "p_name", "p_mfgr", "p_brand", "p_type", "p_size", "p_container", "p_retailprice", "p_comment"],
            "primary_key": ["p_partkey"],
            "foreign_keys": []
        },
        "partsupp": {
            "columns": ["ps_partkey", "ps_suppkey", "ps_availqty", "ps_supplycost", "ps_comment"],
            "primary_key": ["ps_partkey", "ps_suppkey"],
            "foreign_keys": [
                ("ps_partkey", "part.p_partkey"),
                ("ps_suppkey", "supplier.s_suppkey")
            ]
        },
        "region": {
            "columns": ["r_regionkey", "r_name", "r_comment"],
            "primary_key": ["r_regionkey"],
            "foreign_keys": []
        },
        "supplier": {
            "columns": ["s_suppkey", "s_name", "s_address", "s_nationkey", "s_phone", "s_acctbal", "s_comment"],
            "primary_key": ["s_suppkey"],
            "foreign_keys": [("s_nationkey", "nation.n_nationkey")]
        }
    }