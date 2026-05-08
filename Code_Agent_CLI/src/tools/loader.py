"""
工具加载器 - 程序启动时调用，注册所有可用工具

为什么需要这个文件？
- 所有工具的注册集中在一个地方，不用散落在各处
- 新加工具时，只需要在这里加一行 import 和 register 就行
"""
from .registry import ToolRegistry
from .bash import BashTool
from .recall import RecallContentTool, RecallTurnTool
from utils.console import Console


def register_all_tools() -> None:
    """
    注册所有可用的工具

    注意：文件操作工具（read/list/write/grep）已由 MCP filesystem server 替代
    只需保留 BashTool 作为通用命令执行工具
    """
    # 基础工具
    ToolRegistry.register(BashTool)

    # Compression 层配套工具：LLM 自主召回被压缩的完整内容
    ToolRegistry.register(RecallContentTool)

    # MemoryLayer 配套工具：LLM 自主召回历史回合的完整内容
    ToolRegistry.register(RecallTurnTool)


def print_registered_tools() -> None:
    """打印所有已注册的工具（调试用）"""
    Console.info(f"已注册工具：{ToolRegistry.list_names()}")
    for tool in ToolRegistry.list_all():
        Console.info(f"  - {tool.name}")
