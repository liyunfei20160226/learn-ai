"""
工具注册中心 - 管理所有可用工具的注册和查找
"""
from typing import Dict, Type
from tools.base import BaseTool


class ToolRegistry:
    """工具注册中心类"""
    
    _instance = None
    _tools: Dict[str, Type[BaseTool]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        """注册工具类"""
        if not issubclass(tool_class, BaseTool):
            raise TypeError("工具类必须继承自 BaseTool")
            
        if tool_class.name in cls._tools:
            raise ValueError(f"工具 '{tool_class.name}' 已存在")
            
        cls._tools[tool_class.name] = tool_class
        return tool_class
    
    @classmethod
    def get(cls, tool_name: str) -> Type[BaseTool]:
        """根据名称获取工具类"""
        tool_class = cls._tools.get(tool_name)
        if not tool_class:
            raise ValueError(f"工具 '{tool_name}' 未注册")
        return tool_class
    
    @classmethod
    def list(cls) -> Dict[str, Type[BaseTool]]:
        """获取所有工具类"""
        return cls._tools.copy()
    
    @classmethod
    def get_tool_descriptions(cls):
        """获取工具描述信息（用于 Claude API）"""
        descriptions = []
        for tool_name, tool_class in cls._tools.items():
            tool_instance = tool_class()
            descriptions.append(tool_instance.to_dict())
        return descriptions
    
    @classmethod
    def create_tool_instance(cls, tool_name: str) -> BaseTool:
        """创建工具实例"""
        tool_class = cls.get(tool_name)
        return tool_class()


# 装饰器语法注册工具
def register_tool(cls):
    """装饰器：注册工具类"""
    ToolRegistry.register(cls)
    return cls
