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

5) 运行项目(示例)
```bash
python -m src.main "SELECT id, name FROM t1 WHERE status = 'ok' UNION ALL SELECT id, name FROM t2 WHERE status = 'ok' ORDER BY id ASC, name ASC;"
```