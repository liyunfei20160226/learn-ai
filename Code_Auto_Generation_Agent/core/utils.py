"""通用工具函数"""

from pathlib import Path


def safe_resolve_path(working_dir: str | Path, file_path: str) -> Path:
    """安全地解析文件路径，防止路径遍历攻击。

    通过 Path.resolve() 规范化路径后，验证最终路径是否仍然在工作目录内。
    自动移除路径前缀的 "./"，防止 LLM 输出的相对路径问题。

    Args:
        working_dir: 工作目录路径，所有文件操作都不能超出此目录
        file_path: 相对工作目录的文件路径，可以包含任意前缀

    Returns:
        解析后的绝对路径（已规范化，符号链接已解析）

    Raises:
        ValueError: 如果文件路径试图跳出工作目录（路径遍历攻击）
    """
    working_dir = Path(working_dir).resolve()
    norm_path = file_path.lstrip("./")
    raw_path = working_dir / norm_path
    resolved = raw_path.resolve()

    # 使用 Path 相关操作而不是字符串匹配，更安全可靠
    try:
        resolved.relative_to(working_dir)
    except ValueError as e:
        raise ValueError(f"Path traversal detected: {file_path} -> {resolved}") from e

    return resolved
