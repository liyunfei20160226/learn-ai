"""
工具基类 - 定义所有工具的统一接口

为什么需要基类？
1. 统一接口：所有工具都长一个样子，Agent 调用起来不用关心是谁
2. 强制约束：子类必须实现某些方法，否则直接报错
3. 代码复用：通用逻辑写在基类里，不用每个工具重复写

这是「面向对象设计」里的 抽象类/接口 模式。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """
    所有工具的抽象基类

    每个具体的工具都必须继承这个类，并实现以下属性和方法：
    - name: 工具名称（必须是唯一的）
    - description: 工具描述（告诉 Agent 这个工具是干嘛的）
    - input_schema: 工具参数的 JSON Schema（告诉 Agent 参数格式）
    - async run(): 执行工具逻辑
    """

    # ========== 子类必须实现这些属性 ==========

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（必须唯一）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（给 Agent 看的，告诉它什么时候用这个工具）"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """
        工具参数的 JSON Schema

        返回格式示例：
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "required": ["path"]
        }
        """
        pass

    # ========== 子类必须实现这个方法 ==========

    @abstractmethod
    async def run(self, args: Dict[str, Any]) -> str:
        """
        执行工具

        Args:
            args: 工具参数字典（比如 {"path": "main.py"}）

        Returns:
            工具执行结果字符串

        Raises:
            ToolError: 工具执行失败时抛出
        """
        pass

    # ========== 所有工具共用的方法 ==========

    def __str__(self) -> str:
        """方便打印调试"""
        return f"<Tool {self.name}: {self.description}>"

    def __repr__(self) -> str:
        return self.__str__()


class ToolError(Exception):
    """工具执行失败的异常"""
    pass
