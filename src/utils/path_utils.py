import os

def find_file_in_project(filename: str) -> str | None:
    """在项目根目录中查找指定文件"""
    # 从当前文件路径直接构建到仓库根目录的路径
    current_file = os.path.abspath(__file__)
    project_root = current_file.split("SQLoptimize")[0] + "SQLoptimize"
    
    file_path = os.path.join(project_root, filename)
    return file_path if os.path.exists(file_path) else None