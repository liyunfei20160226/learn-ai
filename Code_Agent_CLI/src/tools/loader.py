"""
工具加载器 - 程序启动时调用，注册所有可用工具

为什么需要这个文件？
- 所有工具的注册集中在一个地方，不用散落在各处
- 新加工具时，只需要在这里加一行 import 和 register 就行
"""
from .registry import ToolRegistry
from .read import ReadTool
from .list_dir import ListDirTool


def register_all_tools() -> None:
    """
    注册所有可用的工具

    新加工具时，在这里加一行：
        ToolRegistry.register(NewTool)
    """
    ToolRegistry.register(ReadTool)
    ToolRegistry.register(ListDirTool)


def print_registered_tools() -> None:
    """打印所有已注册的工具（调试用）"""
    print(f"已注册工具：{ToolRegistry.list_names()}")
    for tool in ToolRegistry.list_all():
        print(f"  - {tool.name}: {tool.description}")
