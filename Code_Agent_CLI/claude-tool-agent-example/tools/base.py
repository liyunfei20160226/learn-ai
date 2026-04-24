"""
工具基类定义 - 用于规范工具的注册和调用接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel


class ToolParameter(BaseModel):
    """工具参数基类"""
    pass


class ToolResult(BaseModel):
    """工具执行结果基类"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """所有工具的基类"""
    
    name: str
    description: str
    parameters: Type[ToolParameter]
    returns: Type[ToolResult]
    
    @abstractmethod
    async def run(self, params: ToolParameter) -> ToolResult:
        """执行工具的抽象方法"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 Claude API 所需的工具描述格式"""
        schema = self.parameters.model_json_schema()
        
        # 简化引用类型（Claude API 对 $ref 支持有限）
        properties = {}
        required = []
        
        if schema.get('properties'):
            for field_name, field_schema in schema['properties'].items():
                if '$ref' in field_schema:
                    # 处理引用类型 - 简单化处理
                    properties[field_name] = {'type': 'object', 'description': '复杂类型'}
                else:
                    properties[field_name] = field_schema
            
            required = schema.get('required', [])
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
