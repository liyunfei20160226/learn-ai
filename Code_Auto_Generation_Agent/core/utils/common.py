"""通用工具函数"""

import os
from pathlib import Path


def safe_resolve_path(working_dir: str | Path, file_path: str) -> Path:
    """安全地解析文件路径，防止路径遍历攻击。

    通过 Path.resolve() 规范化路径后，验证最终路径是否仍然在工作目录内。
    "./file.py" 这样的相对路径会被正确处理，"../file.py" 会被检测并阻止。

    Args:
        working_dir: 工作目录路径，所有文件操作都不能超出此目录
        file_path: 相对工作目录的文件路径

    Returns:
        解析后的绝对路径（已规范化，符号链接已解析）

    Raises:
        ValueError: 如果文件路径试图跳出工作目录（路径遍历攻击）
    """
    if not working_dir:
        raise ValueError("working_dir cannot be empty")
    if not file_path:
        raise ValueError("file_path cannot be empty")

    working_dir = Path(working_dir).resolve()

    # 直接拼接，resolve 会处理 ../ 和 ./ 等相对路径组件
    raw_path = working_dir / file_path
    resolved = raw_path.resolve()

    # 安全检查：确保解析后的路径仍然在工作目录内
    # 使用 str.startswith 比 relative_to 更严格，能处理更多边界情况
    working_dir_str = str(working_dir)
    if not working_dir_str.endswith(os.sep):
        working_dir_str += os.sep

    resolved_str = str(resolved)
    if not resolved_str.startswith(working_dir_str) and resolved_str != str(working_dir):
        raise ValueError(f"Path traversal detected: {file_path} -> {resolved}")

    return resolved
