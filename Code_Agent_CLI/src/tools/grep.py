"""
Grep 工具 - 在文件中搜索内容（类似 Unix grep 命令）
"""
import os
import re
from typing import Dict, Any, List, Tuple
from .base import BaseTool, ToolError


class GrepTool(BaseTool):
    """
    在指定目录的文件中搜索文本模式

    参数：
        pattern: 搜索模式（支持正则表达式，必填）
        path: 搜索起始路径（可选，默认当前目录）
        case_sensitive: 是否区分大小写（可选，默认 False）
    """

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "在文件中搜索文本内容，支持正则表达式。参数：pattern（搜索模式，必填），path（搜索路径，可选，默认当前目录），case_sensitive（是否区分大小写，可选，默认False）"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "搜索模式，支持正则表达式",
                },
                "path": {
                    "type": "string",
                    "description": "搜索起始路径，可选，默认当前目录",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写，默认 False",
                },
            },
            "required": ["pattern"],
        }

    async def run(self, args: Dict[str, Any]) -> str:
        """执行搜索"""
        # 1. 校验必填参数
        pattern = args.get("pattern")
        if not pattern:
            raise ToolError("缺少必填参数：pattern")

        search_path = args.get("path", ".")
        case_sensitive = args.get("case_sensitive", False)

        # 2. 安全检查：不允许跳出当前目录
        real_path = os.path.realpath(search_path)
        cwd = os.path.realpath(".")
        if not real_path.startswith(cwd):
            raise ToolError(f"安全限制：不允许访问目录之外的路径：{search_path}")

        # 3. 检查路径是否存在
        if not os.path.exists(search_path):
            raise ToolError(f"路径不存在：{search_path}")

        # 4. 编译正则表达式
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
        except re.error as e:
            raise ToolError(f"无效的正则表达式：{e}")

        # 5. 搜索所有匹配的文件
        matches: List[Tuple[str, int, str]] = []  # (文件路径, 行号, 匹配行内容)
        max_results = 50  # 限制结果数量，避免刷屏

        if os.path.isfile(search_path):
            # 单个文件搜索
            self._grep_file(search_path, regex, matches, max_results)
        else:
            # 目录递归搜索
            for root, dirs, files in os.walk(search_path):
                # 跳过不需要的目录
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules")]

                for filename in files:
                    # 跳过二进制文件和常见的非文本文件
                    if self._is_text_file(filename):
                        file_path = os.path.join(root, filename)
                        self._grep_file(file_path, regex, matches, max_results)

                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break

        # 6. 组装结果
        if not matches:
            return f"未找到匹配内容\n搜索模式：{pattern}\n搜索路径：{search_path}"

        result = f"✅ 搜索完成！找到 {len(matches)} 处匹配\n"
        result += f"搜索模式：{pattern}\n"
        result += f"搜索路径：{search_path}\n"
        result += "=" * 60 + "\n\n"

        for file_path, line_no, line_content in matches:
            # 简化路径显示（去掉 cwd 前缀）
            display_path = os.path.relpath(file_path)
            result += f"{display_path}:{line_no}: {line_content.strip()}\n"

        if len(matches) >= max_results:
            result += f"\n⚠️ 结果已截断，最多显示 {max_results} 条\n"

        return result

    def _grep_file(self, file_path: str, regex: re.Pattern, matches: List[Tuple[str, int, str]], max_results: int):
        """在单个文件中搜索"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if regex.search(line):
                        matches.append((file_path, line_no, line))
                        if len(matches) >= max_results:
                            break
        except (UnicodeDecodeError, PermissionError, OSError):
            # 二进制文件、无权限、打开失败的文件直接跳过
            pass

    def _is_text_file(self, filename: str) -> bool:
        """简单判断是不是文本文件（根据扩展名）"""
        # 常见的文本扩展名
        text_exts = {
            ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".toml",
            ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
            ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php",
            ".sh", ".bash", ".zsh", ".fish",
            ".gitignore", ".dockerignore",
        }

        # 常见的二进制扩展名
        binary_exts = {
            ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so", ".dylib",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".mp3", ".mp4", ".avi", ".mov", ".wav",
        }

        name, ext = os.path.splitext(filename.lower())

        # 如果是已知的二进制扩展名，直接跳过
        if ext in binary_exts:
            return False

        # 如果是已知的文本扩展名，直接接受
        if ext in text_exts:
            return True

        # 没有扩展名的文件（比如 Makefile）也试试
        if not ext:
            return True

        # 其他情况也尝试一下，打不开会在 _grep_file 里捕获
        return True
