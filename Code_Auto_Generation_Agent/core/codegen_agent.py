import hashlib
from pathlib import Path
from typing import Callable, Dict, List

from langchain_core.tools import StructuredTool, tool

from .base_agent import BaseAgent

# === 模块级工具定义：避免每次 Agent 实例化都重新定义 ===
# 注意：需要绑定 self.working_dir 和 self._generated_files_ref 的工具使用闭包工厂创建


def _create_write_file(working_dir: str, generated_files: List[Dict[str, str]],
                       normalize_fn: Callable[[str], str]) -> StructuredTool:
    """创建 write_file 工具（绑定运行时上下文）"""
    @tool
    def write_file(file_path: str, content: str) -> str:
        """新建或写入文件。如果文件已存在，将被覆盖。

        Args:
            file_path: 相对项目根目录的路径，如 "backend/app/main.py"
            content: 文件完整内容
        """
        normalized_path = normalize_fn(file_path)
        full_path = Path(working_dir) / normalized_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        generated_files.append({
            "file_path": normalized_path,
            "content_sha": hashlib.sha256(content.encode()).hexdigest(),
        })

        return f"✓ 文件已写入: {normalized_path} ({len(content)} 字符)"
    return write_file


def _create_append_file(working_dir: str, normalize_fn: Callable[[str], str]) -> StructuredTool:
    """创建 append_file 工具"""
    @tool
    def append_file(file_path: str, content: str) -> str:
        """向已存在的文件追加内容（用于大文件分块写入）

        Args:
            file_path: 相对项目根目录的路径
            content: 要追加的内容
        """
        normalized_path = normalize_fn(file_path)
        full_path = Path(working_dir) / normalized_path

        if not full_path.exists():
            return f"✗ 文件不存在，无法追加: {normalized_path}"

        with open(full_path, "a", encoding="utf-8") as f:
            f.write(content)

        return f"✓ 已追加内容到: {normalized_path}"
    return append_file


def _create_read_file(working_dir: str, normalize_fn: Callable[[str], str]) -> StructuredTool:
    """创建 read_file 工具"""
    @tool
    def read_file(file_path: str) -> str:
        """读取已存在文件的完整内容（用于检查依赖接口）

        Args:
            file_path: 相对项目根目录的路径
        """
        normalized_path = normalize_fn(file_path)
        full_path = Path(working_dir) / normalized_path

        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"✗ 文件不存在: {normalized_path}"
    return read_file


def _create_list_generated_files(generated_files: List[Dict[str, str]]) -> StructuredTool:
    """创建 list_generated_files 工具"""
    @tool
    def list_generated_files() -> str:
        """列出当前任务已生成的所有文件（用于回顾）"""
        if not generated_files:
            return "暂无已生成文件"
        return "已生成文件:\n" + "\n".join(
            f"- {f['file_path']}" for f in generated_files
        )
    return list_generated_files


def _create_finish(generated_files: List[Dict[str, str]]) -> StructuredTool:
    """创建 finish 工具"""
    @tool
    def finish(summary: str) -> str:
        """标记代码生成完成

        Args:
            summary: 代码生成总结
        """
        file_count = len(generated_files)
        return f"✅ 代码生成完成，共生成 {file_count} 个文件\n{summary}"
    return finish


def _create_overwrite_file(write_file_tool: StructuredTool) -> StructuredTool:
    """创建 overwrite_file 工具（是 write_file 的别名）"""
    @tool
    def overwrite_file(file_path: str, content: str) -> str:
        """完全覆盖已有文件（用于错误修复）

        Args:
            file_path: 相对项目根目录的路径
            content: 文件完整内容
        """
        return write_file_tool(file_path, content)
    return overwrite_file


class CodegenAgent(BaseAgent):
    """代码生成 Agent

    通过 ReAct 工具调用模式生成代码文件
    """

    def _get_prompt_template_name(self) -> str:
        return "codegen_agent"

    def _init_tools(self) -> List:
        """定义文件操作工具（使用模块级工厂函数创建）"""
        working_dir = self.working_dir
        generated_files: List[Dict[str, str]] = []  # 运行时缓存
        self._generated_files_ref = generated_files

        normalize_fn = self._normalize_file_path

        write_file = _create_write_file(working_dir, generated_files, normalize_fn)

        return [
            write_file,
            _create_append_file(working_dir, normalize_fn),
            _create_overwrite_file(write_file),  # 是 write_file 的别名
            _create_read_file(working_dir, normalize_fn),
            _create_list_generated_files(generated_files),
            _create_finish(generated_files),
        ]

    def _normalize_file_path(self, file_path: str) -> str:
        """规范化 LLM 输出的 file_path，防止重复写路径前缀

        例：工作目录 = output/todo/backend/
        LLM 写: backend/app/models.py → 规范化为: app/models.py
        LLM 写: app/models.py → 不变
        """
        norm = file_path.lstrip("./")
        if not norm:
            return norm

        fp_parts = norm.replace("\\", "/").split("/")
        working_dir_parts = [
            p for p in str(self.working_dir).replace("\\", "/").split("/") if p
        ]

        for start in range(len(working_dir_parts)):
            match_len = min(len(working_dir_parts) - start, len(fp_parts))
            if all(
                working_dir_parts[start + i] == fp_parts[i]
                for i in range(match_len)
            ):
                remaining = fp_parts[match_len:]
                if remaining:
                    return "/".join(remaining)

        return norm

    def get_generated_files(self) -> List[Dict[str, str]]:
        """获取本次生成的所有文件"""
        return self._generated_files_ref

    def run_with_log(self, user_input: str, verbose: bool = True) -> List[Dict[str, str]]:
        """运行代码生成并输出实时日志

        Args:
            user_input: 任务描述
            verbose: 是否输出详细日志
        """
        def tool_callback(node_name: str, tool_name: str, result: str):
            if verbose:
                if tool_name == "write_file":
                    print(f"  📝 {result}")
                elif tool_name == "append_file":
                    print(f"  ➕ {result}")
                elif tool_name == "overwrite_file":
                    print(f"  ✏️  {result}")
                elif tool_name == "read_file":
                    print(f"  📄 {result}")
                elif tool_name == "list_generated_files":
                    for line in result.split("\n"):
                        print(f"     {line}")
                elif tool_name == "finish":
                    print(f"  🏁  {result}")

        self.run(user_input, tool_callback=tool_callback)
        return self.get_generated_files()
