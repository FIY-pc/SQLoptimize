## 环境要求

- Python 3.10+
- Windows（命令以 PowerShell 为例）

## 安装与运行（Windows）

1) 创建虚拟环境
```bash
python -m venv .venv
```

2) 激活虚拟环境
```bash
.\.venv\Scripts\Activate.ps1
```

3) 安装依赖
```bash
python -m pip install -r requirements.txt
```

4) 配置环境变量（复制 .env.example 为 .env 并填写）
```bash
copy .env.example .env
```

5) 直接运行(示例)
```bash
python -m src.main "SELECT id, name FROM t1 WHERE status = 'ok' UNION ALL SELECT id, name FROM t2 WHERE status = 'ok' ORDER BY id ASC, name ASC;"
```

6) 启动后端服务
```bash
uvicorn src.api:app --reload
```

## API 文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看 API 文档。

访问 `http://localhost:8000/openapi.json` 可获取 OpenAPI 规范。

或者可以看这个在线版：链接: https://hust-sql-optimimize.apifox.cn  访问密码: sqlopt123