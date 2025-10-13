import os
from pathlib import Path

def find_project_root(marker: str = "pyproject.toml") -> Path | None:
    """从当前文件向上查找包含 marker 文件的目录，作为项目根目录"""
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / marker).exists():
            return parent
    return None

def find_file_in_project(filename: str) -> str | None:
    """在项目根目录中查找指定文件"""
    project_root = find_project_root()
    if project_root is None:
        return None
    file_path = project_root / filename
    return str(file_path) if file_path.exists() else None