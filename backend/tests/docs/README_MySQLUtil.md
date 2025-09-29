# MySQL工具模块测试

## 概述

这是 `src/utils/mysql_utils.py` 模块的集成测试套件，直接测试真实的MySQL数据库功能。

## 测试文件

- **`test_mysql_utils.py`** - 主要的测试文件，包含所有测试用例
- **`run_tests.py`** - 便捷的测试运行脚本
- **`conftest.py`** - pytest配置文件
- **`pytest.ini`** - pytest配置

## 环境配置

### 必需的环境变量

```bash
export MYSQL_HOST=your_mysql_host
export MYSQL_PORT=3306
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database
```

或在 `.env` 文件中配置：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=test_db
```

## 运行测试

### 1. 运行所有测试

```bash
# 使用便捷脚本
uv run python tests/run_tests.py

# 或直接使用pytest
uv run pytest tests/test_mysql_utils.py -v
```

### 2. 运行特定测试类型

```bash
# 运行集成测试
uv run python tests/run_tests.py integration

# 运行配置测试
uv run python tests/run_tests.py config
```

### 3. 运行特定测试类

```bash
# 运行MySQLUtils测试
uv run pytest tests/test_mysql_utils.py::TestMySQLUtils -v

# 运行配置测试
uv run pytest tests/test_mysql_utils.py::TestMySQLUtilsConfig -v
```

### 4. 运行特定测试方法

```bash
# 运行特定测试方法
uv run pytest tests/test_mysql_utils.py::TestMySQLUtils::test_mysql_connection -v
```

## 测试覆盖范围

### TestMySQLUtils 类（集成测试）

- ✅ **连接测试**
  - `test_mysql_connection()` - 测试MySQL连接
  - `test_session_context_manager()` - 测试会话上下文管理器

- ✅ **数据库操作测试**
  - `test_get_database_schemas()` - 获取数据库列表
  - `test_get_database_schemas_with_pattern()` - 模式匹配获取数据库

- ✅ **执行计划测试**
  - `test_get_mysql_explain_plan_simple()` - 简单SQL执行计划
  - `test_get_mysql_explain_plan_with_database()` - 指定数据库执行计划

- ✅ **表统计信息测试**
  - `test_get_mysql_table_statistics_information_schema()` - information_schema表统计
  - `test_get_mysql_table_statistics_current_database()` - 当前数据库表统计

- ✅ **TPCH测试**
  - `test_get_tpch_tables_info_if_exists()` - TPCH表信息（如果存在）
  - `test_tpch_schema_structure()` - TPCH schema结构验证

- ✅ **错误处理测试**
  - `test_error_handling_invalid_sql()` - 无效SQL错误处理
  - `test_error_handling_nonexistent_table()` - 不存在表错误处理
  - `test_error_handling_nonexistent_database()` - 不存在数据库错误处理

- ✅ **性能测试**
  - `test_performance_simple_queries()` - 简单查询性能测试

### TestMySQLUtilsConfig 类（配置测试）

- ✅ **配置测试**
  - `test_create_from_settings()` - 从配置创建实例
  - `test_init_with_mysql_database_url()` - MySQL URL初始化
  - `test_init_with_non_mysql_database_url()` - 非MySQL URL异常处理

## 测试特点

### 1. 真实数据库连接
- 直接连接真实的MySQL数据库
- 测试真实的SQL执行和结果
- 验证实际的数据交互

### 2. 智能跳过机制
- 如果未配置MySQL连接，自动跳过测试
- 如果TPCH数据库不存在，跳过相关测试
- 如果当前数据库无法确定，跳过相关测试

### 3. 详细输出
- 打印测试过程中的关键信息
- 显示数据库版本、表信息等
- 提供性能测试结果

### 4. 错误验证
- 测试各种错误情况的处理
- 验证错误消息的正确性
- 确保异常情况下的稳定性

## 故障排除

### 常见问题

1. **连接失败**
   ```
   ❌ 错误: 未配置MySQL连接信息
   ```
   - 检查环境变量是否正确设置
   - 验证MySQL服务是否运行
   - 确认连接参数是否正确

2. **权限不足**
   ```
   ERROR: Access denied for user 'username'@'host'
   ```
   - 检查用户名和密码
   - 确认用户有足够的数据库权限
   - 验证主机访问权限

3. **依赖问题**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   - 确保在项目根目录运行测试
   - 检查Python路径设置

### 调试技巧

1. **详细输出**
   ```bash
   uv run pytest tests/test_mysql_utils.py -v -s
   ```

2. **只运行失败的测试**
   ```bash
   uv run pytest tests/test_mysql_utils.py --lf
   ```

3. **查看覆盖率**
   ```bash
   uv run pytest tests/test_mysql_utils.py --cov=src.utils.mysql_utils
   ```

## 注意事项

1. **数据安全**: 测试不会修改或删除数据，只进行查询操作
2. **性能影响**: 集成测试会实际执行SQL查询，可能对数据库性能有轻微影响
3. **网络依赖**: 需要稳定的网络连接来访问MySQL数据库
4. **权限要求**: 需要足够的数据库权限来执行各种查询操作

## 总结

测试套件提供了对 `mysql_utils.py` 模块的全面测试，确保在实际环境中功能正常。通过真实数据库连接，可以验证：

- ✅ 数据库连接和会话管理
- ✅ SQL查询执行和结果解析
- ✅ 执行计划获取和分析
- ✅ 表统计信息收集
- ✅ 错误处理和异常情况
- ✅ 性能表现和稳定性

这些测试为生产环境中的可靠使用提供了信心保证。
