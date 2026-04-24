"""
ListDir 工具 - 列出目录内容
"""
import os
from typing import Dict, Any
from .base import BaseTool, ToolError


class ListDirTool(BaseTool):
    """
    列出目录下的文件和子目录

    参数：
        path: 目录路径（相对于当前工作目录，可选，默认 .）
    """

    @property
    def name(self) -> str:
        return "list"

    @property
    def description(self) -> str:
        return "列出指定目录下的文件和子目录。参数：path（目录路径，可选，默认当前目录）"

    async def run(self, args: Dict[str, Any]) -> str:
        """执行目录列出"""
        path = args.get("path", ".")

        # 1. 安全检查：不允许跳出当前目录
        real_path = os.path.realpath(path)
        cwd = os.path.realpath(".")
        if not real_path.startswith(cwd):
            raise ToolError(f"安全限制：不允许访问目录之外的路径：{path}")

        # 2. 检查目录是否存在
        if not os.path.exists(path):
            raise ToolError(f"目录不存在：{path}")

        # 3. 检查是不是目录
        if not os.path.isdir(path):
            raise ToolError(f"不是目录：{path}")

        # 4. 列出内容
        try:
            items = os.listdir(path)
        except Exception as e:
            raise ToolError(f"列出目录失败：{e}")

        # 5. 分类：目录和文件分开
        dirs = []
        files = []

        for item in sorted(items):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                dirs.append(item + "/")  # 目录后面加 / 方便识别
            else:
                files.append(item)

        # 6. 组装结果
        result = f"目录：{path}\n"
        result += f"目录数：{len(dirs)}，文件数：{len(files)}\n"
        result += "=" * 50 + "\n"

        if dirs:
            result += "[目录]\n"
            result += "\n".join(dirs) + "\n\n"

        if files:
            result += "[文件]\n"
            result += "\n".join(files) + "\n"

        return result
