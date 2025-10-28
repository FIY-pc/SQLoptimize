# 快速开始

## 环境要求

- Python 3.11+

## 运行

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
# windows
.\.venv\Scripts\Activate.ps1
# linux/mac
source .venv/bin/activate

# 3. 安装依赖
python -m pip install -r requirements.txt

# 4. 配置环境变量（复制 .env.example 为 .env 并填写）

# 运行CLI(示例)
python -m src.main "SELECT id, name FROM t1 WHERE status = 'ok' UNION ALL SELECT id, name FROM t2 WHERE status = 'ok' ORDER BY id ASC, name ASC;"

# 启动后端服务
uvicorn src.api:app --reload
```

如果使用uv
```bash
# 同步依赖
uv sync

# 运行CLI
uv run -m src.main "SELECT id, name FROM t1 WHERE status = 'ok' UNION ALL SELECT id, name FROM t2 WHERE status = 'ok' ORDER BY id ASC, name ASC;"

# 启动后端服务
uv run uvicorn src.api:app --reload
```

使用docker
```bash
# 1. 根据.env.example在仓库根目录配置.env
# 2. 拉起服务(默认开了持久化，需要完全刷新数据可以把volume删掉)
docker compose up -d
```

# 开发指南

## 添加依赖

- 更新requirements.txt:

在requirements.txt手动添加依赖条目

## API 文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看 API 文档。

访问 `http://localhost:8000/openapi.json` 可获取 OpenAPI 规范。

在线版链接: https://hust-sql-optimimize.apifox.cn  访问密码: sqlopt123

## 使用langgraph studio进行agent开发

1. 首先需要去langsmith注册账号，然后拿一个API Key
2. 把API Key填入.env文件中，**并将.env的LANGSMITH_DEV_MODE改为true**
3. 安装langgraph cli
```bash
pip install --upgrade "langgraph-cli[inmem]"
```
4. 运行以下命令
```bash
langgraph dev
```

若有其他问题请查阅 [langgraph文档](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/)