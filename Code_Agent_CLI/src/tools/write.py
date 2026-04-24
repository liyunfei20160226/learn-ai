"""
Write 工具 - 写入文件内容
"""
import os
from pathlib import Path
from typing import Dict, Any
from .base import BaseTool, ToolError


class WriteTool(BaseTool):
    """
    写入内容到本地文件

    参数：
        path: 文件路径（相对于当前工作目录，必填）
        content: 要写入的内容（必填）
        append: 是否追加到文件末尾（可选，默认 False = 覆盖）
    """

    @property
    def name(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return "写入内容到本地文件。参数：path（文件路径，必填），content（要写入的内容，必填），append（是否追加，可选，默认覆盖）"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，相对于当前工作目录",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加到文件末尾，默认 False（覆盖）",
                },
            },
            "required": ["path", "content"],
        }

    async def run(self, args: Dict[str, Any]) -> str:
        """
        执行文件写入

        注意：先用同步 IO 实现，将来性能有要求时可以换成 aiofiles
        """
        # 1. 校验必填参数
        path = args.get("path")
        if not path:
            raise ToolError("缺少必填参数：path")

        content = args.get("content")
        if content is None:
            raise ToolError("缺少必填参数：content")

        append = args.get("append", False)
        mode = "a" if append else "w"

        # 2. 安全检查：不允许跳出当前目录
        real_path = os.path.realpath(path)
        cwd = os.path.realpath(".")
        if not real_path.startswith(cwd):
            raise ToolError(f"安全限制：不允许访问目录之外的文件：{path}")

        # 3. 如果父目录不存在，自动创建
        parent_dir = Path(path).parent
        if parent_dir and not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        # 4. 检查是不是目录
        if os.path.exists(path) and os.path.isdir(path):
            raise ToolError(f"目标是一个目录，不是文件：{path}")

        # 5. 写入文件
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise ToolError(f"写入文件失败：{type(e).__name__}: {e}")

        # 6. 组装结果
        action = "追加" if append else "写入"
        file_size = os.path.getsize(path)
        line_count = content.count("\n") + 1

        result = f"✅ 文件{action}成功！\n"
        result += f"文件：{path}\n"
        result += f"写入行数：{line_count}\n"
        result += f"文件大小：{file_size} 字节\n"

        return result
