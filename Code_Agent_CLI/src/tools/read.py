"""
Read 工具 - 读取文件内容
"""
import os
from typing import Dict, Any
from .base import BaseTool, ToolError


class ReadTool(BaseTool):
    """
    读取本地文件的工具

    参数：
        path: 文件路径（相对于当前工作目录）
        offset: 起始行号（从 0 开始，可选）
        limit: 读取行数（可选，默认全读）
    """

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "读取单个文件的内容。⚠️ 注意：只能用于文件，不能用于目录！查看目录内容请用 list 工具。参数：path（文件路径，必填），offset（起始行号，可选），limit（读取行数，可选）"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，相对于当前工作目录",
                },
                "offset": {
                    "type": "integer",
                    "description": "起始行号（从 0 开始），可选",
                },
                "limit": {
                    "type": "integer",
                    "description": "读取行数，可选，默认全读",
                },
            },
            "required": ["path"],
        }

    async def run(self, args: Dict[str, Any]) -> str:
        """
        执行文件读取

        注意：现在先用同步 IO（Python 的 open 是同步的）
        将来性能有要求时，可以换成 aiofiles（异步文件 IO）
        """
        # 1. 校验必填参数
        path = args.get("path")
        if not path:
            raise ToolError("缺少必填参数：path")

        # 2. 安全检查：不允许跳出当前目录
        real_path = os.path.realpath(path)
        cwd = os.path.realpath(".")
        if not real_path.startswith(cwd):
            raise ToolError(f"安全限制：不允许访问目录之外的文件：{path}")

        # 3. 检查文件是否存在
        if not os.path.exists(path):
            raise ToolError(f"文件不存在：{path}")

        # 4. 检查是不是目录
        if os.path.isdir(path):
            raise ToolError(f"这是一个目录，不是文件：{path}")

        # 5. 读取文件
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            raise ToolError(f"文件编码不是 UTF-8：{path}")
        except Exception as e:
            raise ToolError(f"读取文件失败：{e}")

        # 6. 处理 offset 和 limit
        offset = args.get("offset")
        limit = args.get("limit")

        if offset is not None:
            offset = int(offset)
            lines = lines[offset:]

        if limit is not None:
            limit = int(limit)
            lines = lines[:limit]

        # 7. 组装结果
        content = "".join(lines)
        total_lines = len(lines)

        result = f"文件：{path}\n"
        result += f"总行数：{total_lines}\n"
        if offset is not None:
            result += f"起始行：{offset}\n"
        if limit is not None:
            result += f"读取行数：{limit}\n"
        result += "=" * 50 + "\n"
        result += content

        return result
