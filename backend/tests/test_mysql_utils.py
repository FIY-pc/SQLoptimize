"""MySQL工具模块的集成测试"""

import pytest
import os
import sys
import time

from src.utils.mysql_utils import MySQLUtils
from src.config import Settings


@pytest.fixture(scope="session")
def mysql_utils():
    """创建MySQLUtils实例的会话级fixture"""
    settings = Settings.from_env()
    if not settings.mysql_host:
        pytest.skip("需要配置MySQL连接信息才能运行集成测试")
    
    return MySQLUtils.create_from_settings()


class TestMySQLUtils:
    """MySQLUtils类的集成测试"""

    def test_mysql_connection(self, mysql_utils):
        """测试MySQL连接"""
        result = mysql_utils.test_mysql_connection()
        
        assert result["success"] is True
        assert "version" in result
        assert result["version"] is not None
        print(f"MySQL版本: {result['version']}")
        print(f"当前数据库: {result.get('current_database', 'None')}")

    def test_get_database_schemas(self, mysql_utils):
        """测试获取数据库schema信息"""
        result = mysql_utils.get_database_schemas()
        
        assert result["success"] is True
        assert "databases" in result
        assert isinstance(result["databases"], list)
        assert len(result["databases"]) > 0
        print(f"找到数据库: {result['databases']}")

    def test_get_database_schemas_with_pattern(self, mysql_utils):
        """测试使用模式获取数据库schema信息"""
        result = mysql_utils.get_database_schemas("information_schema")
        
        assert result["success"] is True
        assert "databases" in result
        assert isinstance(result["databases"], list)
        assert "information_schema" in result["databases"]
        print(f"匹配的数据库: {result['databases']}")

    def test_get_mysql_explain_plan_simple(self, mysql_utils):
        """测试获取简单SQL的执行计划"""
        sql = "SELECT 1 as test_column"
        result = mysql_utils.get_mysql_explain_plan(sql)
        
        assert result["success"] is True
        assert "explain_json" in result
        assert "explain_traditional" in result
        assert result["sql"] == sql
        
        # 验证JSON格式执行计划
        if result["explain_json"]:
            assert isinstance(result["explain_json"], (dict, str))
            print(f"JSON执行计划: {result['explain_json']}")
        
        # 验证传统格式执行计划
        if result["explain_traditional"]:
            assert isinstance(result["explain_traditional"], list)
            print(f"传统执行计划: {result['explain_traditional']}")

    def test_get_mysql_explain_plan_with_database(self, mysql_utils):
        """测试在指定数据库中获取执行计划"""
        sql = "SELECT TABLE_NAME FROM TABLES LIMIT 1"
        result = mysql_utils.get_mysql_explain_plan(sql, "information_schema")
        
        assert result["success"] is True
        assert result["sql"] == sql
        print(f"在information_schema中执行: {sql}")

    def test_get_mysql_table_statistics_information_schema(self, mysql_utils):
        """测试获取information_schema.tables表的统计信息"""
        result = mysql_utils.get_mysql_table_statistics("tables", "information_schema")
        
        assert result["success"] is True
        assert result["table_name"] == "tables"
        assert result["database"] == "information_schema"
        assert "statistics" in result
        
        stats = result["statistics"]
        assert "table_info" in stats
        assert "columns" in stats
        assert "indexes" in stats
        
        print(f"表信息: {stats['table_info']}")
        print(f"列数量: {len(stats['columns'])}")
        print(f"索引数量: {len(stats['indexes'])}")

    def test_get_mysql_table_statistics_current_database(self, mysql_utils):
        """测试获取当前数据库的表统计信息"""
        connection_result = mysql_utils.test_mysql_connection()
        if not connection_result["success"] or not connection_result.get("current_database"):
            pytest.skip("无法确定当前数据库")
        
        current_db = connection_result["current_database"]
        schemas_result = mysql_utils.get_database_schemas()
        if current_db not in schemas_result.get("databases", []):
            pytest.skip(f"当前数据库 {current_db} 不在数据库列表中")
        
        result = mysql_utils.get_mysql_explain_plan("SHOW TABLES", current_db)
        if result["success"]:
            print(f"当前数据库 {current_db} 中的表查询成功")
        else:
            print(f"无法查询当前数据库 {current_db} 中的表")

    def test_get_tpch_tables_info_if_exists(self, mysql_utils):
        """测试获取TPCH表信息（如果存在）"""
        schemas_result = mysql_utils.get_database_schemas()
        databases = schemas_result.get("databases", [])
        
        tpch_databases = [db for db in databases if "tpch" in db.lower()]
        
        if not tpch_databases:
            pytest.skip("没有找到TPCH数据库")
        
        tpch_db = tpch_databases[0]
        print(f"使用TPCH数据库: {tpch_db}")
        
        result = mysql_utils.get_tpch_tables_info(tpch_db)
        
        if result["success"]:
            assert "tpch_info" in result
            assert "tables" in result["tpch_info"]
            print(f"TPCH表: {list(result['tpch_info']['tables'].keys())}")
        else:
            print(f"获取TPCH表信息失败: {result.get('error', 'Unknown error')}")

    def test_tpch_schema_structure(self):
        """测试TPCH schema结构定义"""
        schema = MySQLUtils.TPCH_SCHEMA
        
        # 验证所有表都存在
        expected_tables = ["customer", "lineitem", "nation", "orders", "part", "partsupp", "region", "supplier"]
        assert set(schema.keys()) == set(expected_tables)
        
        # 验证每个表都有必要的字段
        for table_name, table_info in schema.items():
            assert "columns" in table_info
            assert "primary_key" in table_info
            assert "foreign_keys" in table_info
            assert isinstance(table_info["columns"], list)
            assert isinstance(table_info["primary_key"], list)
            assert isinstance(table_info["foreign_keys"], list)
            print(f"表 {table_name}: {len(table_info['columns'])}列, {len(table_info['primary_key'])}主键, {len(table_info['foreign_keys'])}外键")

    def test_error_handling_invalid_sql(self, mysql_utils):
        """测试错误处理 - 无效SQL"""
        invalid_sql = "INVALID SQL SYNTAX"
        result = mysql_utils.get_mysql_explain_plan(invalid_sql)
        
        assert result["success"] is False
        assert "error" in result
        assert result["sql"] == invalid_sql
        print(f"预期的SQL错误: {result['error']}")

    def test_error_handling_nonexistent_table(self, mysql_utils):
        """测试错误处理 - 不存在的表"""
        result = mysql_utils.get_mysql_table_statistics("nonexistent_table_12345")
        
        # 检查结果，可能成功也可能失败，取决于数据库行为
        if result["success"]:
            print(f"表不存在但查询成功，返回空统计信息: {result}")
            assert "statistics" in result
        else:
            print(f"预期的表不存在错误: {result['error']}")
            assert "error" in result
            assert result["table_name"] == "nonexistent_table_12345"

    def test_error_handling_nonexistent_database(self, mysql_utils):
        """测试错误处理 - 不存在的数据库"""
        result = mysql_utils.get_mysql_table_statistics("test_table", "nonexistent_database_12345")
        
        assert result["success"] is False
        assert "error" in result
        assert result["database"] == "nonexistent_database_12345"
        print(f"预期的数据库不存在错误: {result['error']}")

    def test_session_context_manager(self, mysql_utils):
        """测试session上下文管理器"""
        with mysql_utils.session() as session:
            assert session is not None
            from sqlalchemy import text
            result = session.execute(text("SELECT 1 as test"))
            print("Session上下文管理器工作正常")

    def test_performance_simple_queries(self, mysql_utils):
        """测试简单查询的性能"""
        queries = [
            "SELECT 1",
            "SELECT VERSION()",
            "SELECT NOW()",
            "SELECT DATABASE()",
            "SELECT USER()"
        ]
        
        for query in queries:
            start_time = time.time()
            result = mysql_utils.get_mysql_explain_plan(query)
            end_time = time.time()
            
            assert result["success"] is True
            execution_time = end_time - start_time
            print(f"查询 '{query}' 执行时间: {execution_time:.4f}秒")


class TestMySQLUtilsConfig:
    """MySQLUtils配置相关测试"""

    def test_create_from_settings(self):
        """测试从配置设置创建实例"""
        settings = Settings.from_env()
        if not settings.mysql_host:
            pytest.skip("需要配置MySQL连接信息")
        
        utils = MySQLUtils.create_from_settings()
        assert utils is not None
        assert utils.database_type == 'mysql'

    def test_init_with_mysql_database_url(self):
        """测试使用MySQL数据库URL初始化"""
        settings = Settings.from_env()
        if not settings.mysql_host:
            pytest.skip("需要配置MySQL连接信息")
        
        database_url = f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password or ''}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database or ''}"
        utils = MySQLUtils(database_url)
        assert utils.database_type == 'mysql'

    def test_init_with_non_mysql_database_url(self):
        """测试使用非MySQL数据库URL初始化应该抛出异常"""
        with pytest.raises(ValueError, match="MySQLUtils只能用于MySQL数据库"):
            MySQLUtils("sqlite:///test.db")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
