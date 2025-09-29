# SQL 等价性校验（WSL）

前置
- 在 WSL 中运行（Ubuntu/Debian）
- Python 3.8+，Java 17
- 用python来调用java环境

使用
1) 进入项目目录（WSL 路径示例）：
```bash
cd /mnt/e/SQL等价性校验
```

2) 运行示例：
```bash
python3 test.py
```

编辑 SQL 与 Schema
- 打开 test.py 最后几行，修改：
  - sql1 / sql2：两条要对比的 SQL （需要符合calcite规范）
  - schema：对应表的 DDL（字符串）

示例（已内置）：
- schema: CREATE TABLE users(id INT, age INT);
- sql1: SELECT id FROM users WHERE age > 18
- sql2: SELECT id FROM users WHERE NOT (age <= 18)

输出
- success: True/False 等价性检验过程是否执行成功
- equivalent：True/False 两条 SQL 是否等价
- details：等价性检验过程的详细信息