from typing import List

from langchain_core.tools import tool

from .base_agent import BaseAgent


class FixAgent(BaseAgent):
    """错误修复专用 Agent

    读取错误信息 → 定位文件 → 读取文件内容 → 修复并覆盖
    """

    def _get_prompt_template_name(self) -> str:
        return "fix_agent"

    def _init_tools(self) -> List:
        """定义修复工具"""
        working_dir = self.working_dir

        @tool
        def read_file(file_path: str) -> str:
            """读取已存在文件的完整内容

            Args:
                file_path: 相对项目根目录的路径
            """
            from pathlib import Path
            full_path = Path(working_dir) / file_path

            if full_path.exists():
                with open(full_path, "r", encoding="utf-8"):
                    return f"✓ 已读取: {file_path}"
            return f"✗ 文件不存在: {file_path}"

        @tool
        def overwrite_file(file_path: str, content: str) -> str:
            """完全覆盖已有文件以修复错误

            Args:
                file_path: 相对项目根目录的路径
                content: 修复后的完整文件内容
            """
            from pathlib import Path
            full_path = Path(working_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"✓ 文件已修复: {file_path} ({len(content)} 字符)"

        @tool
        def list_project_files() -> str:
            """列出项目中所有文件，帮助定位问题文件"""
            from pathlib import Path
            project_path = Path(working_dir)
            files = []
            for f in project_path.rglob("*"):
                if f.is_file() and "__pycache__" not in str(f) and ".git" not in str(f):
                    rel_path = f.relative_to(project_path)
                    files.append(str(rel_path))
            return "\n".join(sorted(files))

        @tool
        def finish(summary: str) -> str:
            """标记代码修复完成

            Args:
                summary: 修复总结
            """
            return f"✅ 代码修复完成\n{summary}"

        return [read_file, overwrite_file, list_project_files, finish]

    def run_with_log(self, user_input: str, verbose: bool = True) -> None:
        """运行修复并输出实时日志

        Args:
            user_input: 错误信息
            verbose: 是否输出详细日志
        """
        def tool_callback(node_name: str, tool_name: str, result: str):
            if verbose:
                if tool_name == "read_file":
                    print(f"  📄 {result}")
                elif tool_name == "overwrite_file":
                    print(f"  ✏️  {result}")
                elif tool_name == "list_project_files":
                    print("  📂 项目文件:")
                    for line in result.split("\n"):
                        print(f"     - {line}")
                elif tool_name == "finish":
                    print(f"  🏁  {result}")

        self.run_stream(user_input, tool_callback=tool_callback)
