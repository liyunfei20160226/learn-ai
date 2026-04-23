from pathlib import Path
from typing import List

from langchain_core.tools import StructuredTool, tool

from ..utils import run_shell_command, safe_resolve_path
from .base_agent import BaseAgent

# === 模块级工具工厂：避免每次实例化都重新定义嵌套函数 ===


def _detect_lint_command(working_dir: str) -> List[str]:
    """自动检测项目的 lint 命令"""
    project_path = Path(working_dir)
    commands = []

    if (project_path / "pyproject.toml").exists():
        commands.append("uv run ruff check .")
    elif (project_path / "package.json").exists():
        commands.append("npm run lint")

    return commands


def _detect_type_check_command(working_dir: str) -> List[str]:
    """自动检测项目的类型检查命令"""
    project_path = Path(working_dir)
    commands = []

    if (project_path / "pyproject.toml").exists():
        commands.append("uv run mypy .")
    elif (project_path / "package.json").exists():
        commands.append("npm run type-check")

    return commands


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

        if not full_path.exists():
            return f"✗ 文件不存在: {file_path}"
        if not full_path.is_file():
            return f"✗ 不是文件: {file_path}"

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except PermissionError:
            return f"✗ 没有读取权限: {file_path}"
        except UnicodeDecodeError:
            return f"✗ 文件编码不是 UTF-8: {file_path}"
        except IOError as e:
            return f"✗ 读取文件失败: {file_path}, 错误: {str(e)}"
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

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return f"✗ 没有创建目录权限: {full_path.parent}"
        except IOError as e:
            return f"✗ 创建目录失败: {str(e)}"

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            return f"✗ 没有写入权限: {file_path}"
        except IOError as e:
            return f"✗ 写入文件失败: {file_path}, 错误: {str(e)}"

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


def _create_quick_lint_check(working_dir: str) -> StructuredTool:
    """创建快速 lint 检查工具"""
    @tool
    def quick_lint_check() -> str:
        """运行快速 lint 检查，看看当前修复效果如何

        这是快速自检工具，不会影响整体修复流程。
        如果你发现修复后还是有错误，可以继续修改，直到满意为止。
        """
        commands = _detect_lint_command(working_dir)
        if not commands:
            return "⚠️  未检测到 lint 命令，跳过快速检查"

        all_output = []
        for cmd in commands:
            success, output = run_shell_command(cmd, working_dir, timeout=120)
            if success:
                all_output.append(f"✅ {cmd} 检查通过")
            else:
                all_output.append(f"❌ {cmd} 检查失败:\n{output}")

        return "\n\n".join(all_output)
    return quick_lint_check


def _create_quick_type_check(working_dir: str) -> StructuredTool:
    """创建快速类型检查工具"""
    @tool
    def quick_type_check() -> str:
        """运行快速类型检查，看看当前修复效果如何

        这是快速自检工具，不会影响整体修复流程。
        如果你发现修复后还是有错误，可以继续修改，直到满意为止。
        """
        commands = _detect_type_check_command(working_dir)
        if not commands:
            return "⚠️  未检测到类型检查命令，跳过快速检查"

        all_output = []
        for cmd in commands:
            success, output = run_shell_command(cmd, working_dir, timeout=180)
            if success:
                all_output.append(f"✅ {cmd} 类型检查通过")
            else:
                all_output.append(f"❌ {cmd} 类型检查失败:\n{output}")

        return "\n\n".join(all_output)
    return quick_type_check


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
            _create_quick_lint_check(working_dir),
            _create_quick_type_check(working_dir),
            _FINISH_TOOL,  # 无状态，重用单例
        ]

    def run_with_log(self, user_input: str, verbose: bool = True) -> bool:
        """运行修复并输出实时日志

        Args:
            user_input: 错误信息
            verbose: 是否输出详细日志

        Returns:
            是否正常完成（调用了 finish 工具），False 表示被强制终止
        """
        callback = self.default_tool_callback if verbose else None
        result = self.run(user_input, tool_callback=callback)

        # 检查是否调用了 finish 工具（判断是否正常完成）
        tool_counts = self.get_tool_call_counts(result)
        finished_normally = "finish" in tool_counts

        if not finished_normally and verbose:
            print("  ⚠️  Agent 被强制终止（达到最大迭代次数或超时）")

        return finished_normally
