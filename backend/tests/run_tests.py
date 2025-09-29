#!/usr/bin/env python3
"""运行MySQL工具模块测试的脚本"""

import subprocess
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Settings


def check_mysql_config():
    """检查MySQL配置"""
    settings = Settings.from_env()
    
    print("检查MySQL配置...")
    print(f"MySQL Host: {settings.mysql_host or '未设置'}")
    print(f"MySQL Port: {settings.mysql_port}")
    print(f"MySQL User: {settings.mysql_user or '未设置'}")
    print(f"MySQL Database: {settings.mysql_database or '未设置'}")
    
    if not settings.mysql_host:
        print("\n❌ 错误: 未配置MySQL连接信息")
        print("请设置以下环境变量:")
        print("  MYSQL_HOST=your_mysql_host")
        print("  MYSQL_PORT=3306")
        print("  MYSQL_USER=your_username")
        print("  MYSQL_PASSWORD=your_password")
        print("  MYSQL_DATABASE=your_database")
        return False
    
    print("✅ MySQL配置检查通过")
    return True


def run_tests(test_type="all"):
    """运行测试"""
    print("=" * 60)
    print("MySQL工具模块测试")
    print("=" * 60)
    
    # 检查配置
    if not check_mysql_config():
        return False
    
    print(f"\n开始运行{test_type}测试...")
    print("-" * 40)
    
    # 构建测试命令
    if test_type == "all":
        test_cmd = [
            sys.executable, "-m", "pytest", 
            "tests/test_mysql_utils.py",
            "-v", "--tb=short", "--color=yes"
        ]
    elif test_type == "integration":
        test_cmd = [
            sys.executable, "-m", "pytest", 
            "tests/test_mysql_utils.py::TestMySQLUtils",
            "-v", "--tb=short", "--color=yes"
        ]
    elif test_type == "config":
        test_cmd = [
            sys.executable, "-m", "pytest", 
            "tests/test_mysql_utils.py::TestMySQLUtilsConfig",
            "-v", "--tb=short", "--color=yes"
        ]
    else:
        print(f"❌ 未知的测试类型: {test_type}")
        return False
    
    print("执行命令:", " ".join(test_cmd))
    print()
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    result = subprocess.run(test_cmd)
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ 测试全部通过!")
    else:
        print("❌ 测试失败!")
    print("=" * 60)
    
    return result.returncode == 0


def main():
    """主函数"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"
    
    success = run_tests(test_type)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
