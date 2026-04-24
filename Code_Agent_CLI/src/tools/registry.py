"""
工具注册表 - 管理所有可用的工具

设计模式：
- 单例模式：全局只有一个注册表实例
- 工厂模式：按名称创建工具实例

为什么需要注册表？
1. Agent 不需要知道具体有哪些工具，只需要按名字找
2. 新加工具只需要注册，不需要改 Agent 代码
3. 统一管理，防止重名
"""
from typing import Dict, Type, List
from .base import BaseTool


class ToolRegistry:
    """
    工具注册表 - 全局唯一

    使用方法：
        # 注册
        ToolRegistry.register(ReadTool)

        # 查找
        tool = ToolRegistry.get("read")

        # 执行
        result = await tool.run(args)
    """

    # 存储所有注册的工具类：{工具名称: 工具类}
    _tools: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> None:
        """
        注册一个工具类

        Args:
            tool_class: 工具类（不是实例！是类本身）

        Raises:
            ValueError: 如果名称重复了
        """
        # 先实例化一下，拿到 name
        # （因为 name 是 property，必须实例化才能访问）
        dummy = tool_class()
        name = dummy.name

        if name in cls._tools:
            raise ValueError(f"工具名称冲突：{name} 已经被注册了")

        cls._tools[name] = tool_class

    @classmethod
    def get(cls, name: str) -> BaseTool:
        """
        根据名称获取工具实例

        Args:
            name: 工具名称

        Returns:
            工具实例

        Raises:
            ValueError: 如果工具不存在
        """
        tool_class = cls._tools.get(name)
        if tool_class is None:
            raise ValueError(f"未知工具：{name}。可用工具：{list(cls._tools.keys())}")

        return tool_class()  # 每次都创建新实例，保证状态隔离

    @classmethod
    def list_names(cls) -> List[str]:
        """获取所有可用工具的名称列表"""
        return list(cls._tools.keys())

    @classmethod
    def list_all(cls) -> List[BaseTool]:
        """获取所有工具实例（用于调试打印）"""
        return [tool_class() for tool_class in cls._tools.values()]

    @classmethod
    def clear(cls) -> None:
        """清空所有注册（主要用于单元测试）"""
        cls._tools.clear()
