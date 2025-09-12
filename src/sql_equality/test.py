import subprocess
import os
import shutil


def verify_sql_equivalence(jar_path, sql1, sql2, schema, java_path=None, z3_lib_path="./lib"):
    """
    调用SQL验证工具，显式传递Z3库路径解决依赖问题

    参数:
        z3_lib_path (str): Z3库所在目录（如/lib或/usr/local/z3/lib）
    """
    # 1. 处理Java路径
    if java_path:
        if not os.path.isfile(java_path) or not os.access(java_path, os.X_OK):
            return {"success": False, "error": f"无效的Java路径: {java_path}"}
        java_executable = java_path
    else:
        java_executable = shutil.which("java")
        if not java_executable:
            return {"success": False, "error": "未找到Java环境，请安装或指定java_path"}

    # 2. 处理JAR包路径
    absolute_jar_path = os.path.abspath(jar_path)
    if not os.path.exists(absolute_jar_path):
        return {"success": False, "error": f"JAR包不存在: {absolute_jar_path}"}

    # 3. 处理Z3库路径（关键：传递环境变量）
    # 获取当前环境变量的副本
    env = os.environ.copy()
    if z3_lib_path:
        # 验证Z3库目录是否存在
        if not os.path.isdir(z3_lib_path):
            return {"success": False, "error": f"Z3库目录不存在: {z3_lib_path}"}
        # 设置LD_LIBRARY_PATH（Linux/WSL）或DYLD_LIBRARY_PATH（macOS）
        if os.name == "posix":
            lib_env = "LD_LIBRARY_PATH" if os.uname().sysname != "Darwin" else "DYLD_LIBRARY_PATH"
            abs_z3 = os.path.abspath(z3_lib_path)
            env[lib_env] = abs_z3 if not env.get(lib_env) else f"{abs_z3}:{env.get(lib_env)}"

    # 4. 构建命令列表
    command = [
        java_executable,
        f"-Djava.library.path={os.path.abspath(z3_lib_path)}",
        "-jar",
        absolute_jar_path,
        "-sql1", sql1,
        "-sql2", sql2,
        "-schema", schema
    ]

    try:
        # 执行命令时传递环境变量env
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            env=env  # 关键：传入包含Z3库路径的环境变量
        )

        # 解析结果
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "未知错误"
            return {"success": False, "error": f"执行失败: {error_msg}"}

        output = result.stdout.strip()

        # 打印原始输出（调试用）
        # print (output)
        
        equivalent = None
        details = output

        # 解析中文提示
        target_line = None
        for line in output.splitlines():
            if "SQL等价性验证结果: " in line:
                target_line = line
                break
        if target_line:
            if "NEQ" in target_line:
                equivalent = False
            elif "EQ" in target_line:
                equivalent = True

        if equivalent is not None:
            return {
                "success": True,
                "equivalent": bool(equivalent),
                "details": details
            }
        else:
            # 如果无法解析出明确结果，返回原始输出，交由上层判断
            return {
                "success": False,
                "error": "无法从输出解析出SQL等价性结果",
                "raw_output": output
            }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "执行超时（60s）"}
    except Exception as e:
        return {"success": False, "error": f"未知异常: {e}"}


if __name__ == "__main__":
    jar = "./lib/sqlsolver-v1.1.0.jar"
    # 将这三段替换为你真实的 SQL 和 schema（支持使用文件内容字符串）

    # 示例一
    sql1 = "SELECT id FROM users WHERE age > 18"
    sql2 = "SELECT id FROM users WHERE NOT (age <= 18)"
    schema = "CREATE TABLE users(id INT, age INT);"

    # 示例二
    # sql1 = "SELECT id FROM users WHERE age BETWEEN 10 AND 20;"
    # sql2 = "SELECT id FROM users WHERE age >= 10 AND age <= 20;"
    # schema = "CREATE TABLE users(id INT PRIMARY KEY, age INT NOT NULL);"

    # 示例三
    # sql1 = "SELECT id FROM employees WHERE dept_id IN (1, 2, 3);"
    # sql2 = "SELECT id FROM employees WHERE dept_id = 1 OR dept_id = 2 OR dept_id = 3;"
    # schema = "CREATE TABLE employees(id INT PRIMARY KEY, dept_id INT NOT NULL);"

    # 示例四
    # sql1 = "SELECT DISTINCT id FROM t1;"
    # sql2 = "SELECT id FROM t1;"
    # schema = "CREATE TABLE t1(id INT PRIMARY KEY, v INT NOT NULL);"

    # 示例五
    # sql1 = "SELECT DISTINCT v FROM t2;"
    # sql2 = "SELECT v FROM t2;"
    # schema = "CREATE TABLE t2(id INT PRIMARY KEY, v INT NOT NULL);"

    result = verify_sql_equivalence(jar, sql1, sql2, schema, java_path=None, z3_lib_path="./lib")
    print(result)
         