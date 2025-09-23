# SQLoptimize 模块说明

## 核心模块

### `config.py`
- 配置管理模块
- 提供 `get_settings()` 函数获取全局配置
- 包含数据库连接、LLM API、JWT等配置项

### `llm.py`
- LLM客户端封装
- 提供同步和异步的聊天接口
- 支持流式输出和状态管理

## 数据库相关

### `db/registry.py`
- 数据库连接注册表
- 支持MySQL、PostgreSQL、SQLite
- 提供同步和异步连接管理

### `utils/mysql_utils.py` ⭐
- **Graph模块开发推荐**
- MySQL数据库工具类
- 提供执行计划获取、表统计信息收集
- 支持TPCH基准测试数据集
- 可用于Graph节点中的数据库分析

## 流处理

### `stream/stream_writer.py` ⭐
- **Graph模块开发推荐**
- 流式数据写入器
- 支持实时数据流输出
- 可用于Graph节点的流式结果输出

### `stream/mapper.py`
- 流数据映射器
- 数据转换和格式化

### `schemas/stream_chunk.py`
- 流数据块定义
- 包含LLM输出块等数据结构

## Graph相关

### `graph/`
- `enhanced_graph.py` - 增强版Graph实现
- `enhanced_nodes.py` - 增强版节点实现
- `graph_async.py` - 异步Graph
- `nodes_async.py` - 异步节点
- `nodes.py` - 基础节点实现
- `simple_gragh.py` - 简单Graph实现
- `sql_analyzer.py` - SQL分析器
- `state.py` - Graph状态管理

## API接口

### `api/`
- `app.py` - FastAPI应用主入口
- `middleware.py` - 中间件
- `router/` - 路由模块
  - `ai_router.py` - AI相关接口
  - `auth_router.py` - 认证接口
  - `database_router.py` - 数据库接口
  - `model_router.py` - 模型接口
- `repository/` - 数据访问层
- `service_db.py` - 数据库服务

## 工具模块

### `utils/`
- `mysql_utils.py` ⭐ - MySQL工具（推荐用于Graph开发）
- `time_utils.py` - 时间工具

### `sql_equality/`
- SQL等价性校验模块
- 包含Z3求解器和SQL求解器

## 模型定义

### `models/`
- `base.py` - 基础模型
- `database_connection.py` - 数据库连接模型
- `model_connection.py` - 模型连接模型
- `user.py` - 用户模型

## 管道

### `pipelines.py`
- 数据处理管道
- 集成各种处理步骤

## Graph模块开发建议

**推荐使用的模块：**
1. **`utils/mysql_utils.py`** - 用于数据库分析和执行计划获取
2. **`stream/stream_writer.py`** - 用于流式输出结果
3. **`graph/state.py`** - 用于状态管理
4. **`config.py`** - 用于配置获取
5. **`llm.py`** - 用于LLM调用

**使用示例：**
```python
from src.utils.mysql_utils import MySQLUtils
from src.stream.stream_writer import StreamWriter
from src.graph.state import State

# 在Graph节点中使用
def analyze_sql_node(state: State):
    mysql_utils = MySQLUtils.create_from_settings() # 加载配置中的MySQL
    # mysql_utils=MySQLUtils(database_url) 使用任意数据库

    stream_writer = state.get("stream_writer")
    
    # 获取执行计划
    explain_result = mysql_utils.get_mysql_explain_plan(sql)
    
    # 流式输出结果
    if stream_writer:
        stream_writer.write(explain_result)
```
