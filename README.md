# SQLoptimize

**第三届开放原子大赛 — OpenTenBase-TXSQL SQL 改写优化挑战赛 · 一等奖获奖项目**

SQLoptimize 是一个面向 OpenTenBase 的智能 SQL 改写优化引擎。基于 LangGraph 编排 LLM 推理与数据库分析工具，自动识别低效 SQL、生成等价改写方案，并配合关系代数验证与 LLM 语义校验双重机制保证改写正确性。在 TPC-DS 基准测试中平均加速比达 32.8%。

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.6.10+-1C3C3C?logo=langchain)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-15.0+-000000?logo=next.js)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](LICENSE)

---

## 项目背景

本作品（团队 **IDSM-DB**，华中科技大学）参与 **[第三届开放原子大赛 — OpenTenBase-TXSQL SQL 改写优化挑战赛](https://competition.openatom.tech/competitionInfo?id=8126a8c6f7012422a9c62e44214fb10b)**，由 [开放原子开源基金会](https://www.openatom.org) 主办、[腾讯云](https://cloud.tencent.com) 承办。

赛题旨在基于 TXSQL 优化器与执行框架，探索 SQL 改写优化技术，使数据库能够更智能地识别低效 SQL，自动进行等价高效的查询重写，并保证改写前后的语义等价性，从而显著提升多表关联查询、嵌套子查询、CTE 等复杂场景下的 SQL 执行效率。

本项目荣获 **一等奖**。

---

## 功能

| 功能 | 说明 |
|------|------|
| 智能改写 | LLM 驱动的 SQL 等价改写，支持多表关联、嵌套子查询、CTE 等复杂场景 |
| 执行计划分析 | 自动获取 MySQL EXPLAIN FORMAT=JSON，对比改写前后的计划与成本 |
| 语义等价性校验 | LLM + Z3 / SQLSolver 双重校验，确保改写正确性 |
| 表统计信息采集 | 自动解析 SQL 涉及的表，采集列类型、索引、基数等统计信息辅助优化决策 |
| 流式对话 | 基于 SSE 的流式输出，实时查看优化过程与中间结果 |
| Web 管理界面 | Next.js 前端，支持多用户、模型连接管理、数据库连接管理、Schema 管理 |

---

## 架构

```
用户输入 (Web UI / API / CLI)
       │
       ▼
┌───────────────────────┐
│    FastAPI + Uvicorn   │── SSE 流式输出
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│   LangGraph Agent      │── 有向图编排各节点
└───────┬───────────────┘
        │
        ├── 查询计划获取节点     ── MySQL EXPLAIN
        ├── 统计信息采集节点     ── 表/列/索引统计
        ├── LLM 优化生成节点     ── 多方案改写
        ├── 等价性校验节点       ── Z3 / SQLSolver / LLM 三重校验
        ├── 成本对比节点         ── 改写前后执行计划成本
        └── 报告生成节点         ── 汇总优化结果
                │
                ▼
        ┌───────────────┐
        │   MySQL 数据库  │── EXPLAIN + 统计信息
        └───────────────┘
```

### Agent 工作流

```
输入 SQL → 获取执行计划 → 采集统计信息
    → LLM 生成优化方案 → 校验等价性
    → 对比成本 → 输出优化报告
        ↑__________失败重试__________|
```

---

## 快速开始

### 环境要求

- Python 3.13+
- MySQL 数据库（用于 EXPLAIN 分析）
- LLM API 服务（阿里云通义千问、DeepSeek、OpenAI 兼容接口等）
- Java 17（可选，用于 SQLSolver 等价性校验）
- Node.js 20+（可选，用于前端开发）

### 后端启动

```bash
git clone <your-repo-url>
cd sqloptimize

# 安装依赖
pip install -e .[dev]

# 配置环境变量
cp .env.example .env
```

编辑 `.env`：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL=qwen-plus

# 服务数据库（默认 SQLite，生产建议 PostgreSQL）
SERVICE_DB_URL=sqlite:///data/sqloptimize.db

# MySQL 连接（用于 EXPLAIN 分析）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=tpch_1g
```

```bash
# 启动 API 服务
uvicorn src.api.app:app --reload --port 8000
```

### CLI 模式

```bash
python -m src.main "SELECT ..." --db_schema "CREATE TABLE ..."
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000` 进入 Web 界面。

---

## 优化案例

TPC-DS 基准测试中的典型优化效果：

| 查询 | 改写前成本 | 改写后成本 | 改善比例 |
|------|-----------|-----------|---------|
| Q17 (小表关联聚合) | 124,582 | 42,176 | 66.1% |
| Q25 (多层嵌套子查询) | 287,634 | 95,248 | 66.9% |
| Q67 (CTE 多重引用) | 523,891 | 181,234 | 65.4% |

> 成本值为 MySQL EXPLAIN FORMAT=JSON 的 `query_cost`，实际性能提升取决于数据分布与执行环境。

---

## 技术栈

| 组件 | 选型 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| Agent 框架 | LangGraph (StateGraph) |
| LLM SDK | LangChain (OpenAI / DeepSeek / 阿里云 DashScope) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库驱动 | aiomysql / asyncpg / aiosqlite |
| 等价性校验 | Z3 Prover + SQLSolver + LLM |
| 前端 | Next.js 15 + assistant-ui |
| 认证 | JWT (python-jose) |
| 流式输出 | Server-Sent Events (SSE) |

---

## 项目结构

```
backend/
├── src/
│   ├── api/            # FastAPI 路由、Repository、Middleware
│   ├── graph/          # LangGraph Agent 节点与状态定义
│   │   ├── agent/      # LLM 节点（改写、校验、报告生成）
│   │   ├── tools/      # 工具（EXPLAIN、统计信息、等价性校验）
│   │   └── state/      # 图状态定义
│   ├── llm/            # LLM 客户端封装
│   ├── models/         # SQLAlchemy 数据模型
│   ├── db/             # 数据库注册与 Session 管理
│   ├── schemas/        # Pydantic 数据模型
│   ├── stream/         # SSE 流式输出
│   └── utils/          # 工具函数
├── frontend/           # Next.js 前端
├── docker/             # Docker Compose 部署配置
└── tests/              # 测试
```

---

## 许可证

Apache License 2.0