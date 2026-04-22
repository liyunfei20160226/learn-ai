from pathlib import Path
from typing import List

from langchain_core.tools import StructuredTool, tool

from .base_agent import BaseAgent
from .utils import safe_resolve_path

# === 模块级工具工厂：避免每次实例化都重新定义嵌套函数 ===


def _create_read_file(working_dir: str) -> StructuredTool:
    """创建 read_file 工具（带路径安全检查）"""
    @tool
    def read_file(file_path: str) -> str:
        """读取已存在文件的完整内容

        Args:
            file_path: 相对项目根目录的路径
        """
        try:
            full_path = safe_resolve_path(working_dir, file_path)
        except ValueError as e:
            return f"✗ {e}"

        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"✗ 文件不存在: {file_path}"
    return read_file


def _create_overwrite_file(working_dir: str) -> StructuredTool:
    """创建 overwrite_file 工具（带路径安全检查）"""
    @tool
    def overwrite_file(file_path: str, content: str) -> str:
        """完全覆盖已有文件以修复错误

        Args:
            file_path: 相对项目根目录的路径
            content: 修复后的完整文件内容
        """
        try:
            full_path = safe_resolve_path(working_dir, file_path)
        except ValueError as e:
            return f"✗ {e}"

        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✓ 文件已修复: {file_path} ({len(content)} 字符)"
    return overwrite_file


def _create_list_project_files(working_dir: str) -> StructuredTool:
    """创建 list_project_files 工具"""
    @tool
    def list_project_files() -> str:
        """列出项目中所有文件，帮助定位问题文件"""
        project_path = Path(working_dir).resolve()
        files = []
        for f in project_path.rglob("*"):
            if f.is_file() and "__pycache__" not in str(f) and ".git" not in str(f):
                rel_path = f.relative_to(project_path)
                files.append(str(rel_path))
        return "\n".join(sorted(files))
    return list_project_files


@tool
def finish(summary: str) -> str:
    """标记代码修复完成

    Args:
        summary: 修复总结
    """
    return f"✅ 代码修复完成\n{summary}"


# 无状态依赖的工具直接定义为模块级单例
_FINISH_TOOL = finish


class FixAgent(BaseAgent):
    """错误修复专用 Agent

    读取错误信息 → 定位文件 → 读取文件内容 → 修复并覆盖
    """

    def _get_prompt_template_name(self) -> str:
        return "fix_agent"

    def _init_tools(self) -> List:
        """定义修复工具（使用模块级工厂函数创建）"""
        working_dir = self.working_dir

        return [
            _create_read_file(working_dir),
            _create_overwrite_file(working_dir),
            _create_list_project_files(working_dir),
            _FINISH_TOOL,  # 无状态，重用单例
        ]

    def run_with_log(self, user_input: str, verbose: bool = True) -> None:
        """运行修复并输出实时日志

        Args:
            user_input: 错误信息
            verbose: 是否输出详细日志
        """
        callback = self.default_tool_callback if verbose else None
        self.run(user_input, tool_callback=callback)
