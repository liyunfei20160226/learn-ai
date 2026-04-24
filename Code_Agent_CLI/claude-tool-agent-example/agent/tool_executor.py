"""
工具执行器 - 负责解析和执行工具调用
"""
from typing import Dict, Any, Optional
from agent.tool_registry import ToolRegistry
from tools.base import ToolResult
import json


class ToolExecutionError(Exception):
    """工具执行异常"""
    pass


class ToolExecutor:
    """工具执行器类"""
    
    @staticmethod
    def parse_tool_call(tool_call_data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        解析 Claude 返回的工具调用数据
        
        Args:
            tool_call_data: Claude 返回的工具调用JSON数据
            
        Returns:
            工具名称和参数字典
        """
        tool_name = tool_call_data.get("name")
        tool_params = tool_call_data.get("parameters", {})
        
        if not tool_name:
            raise ToolExecutionError("无效的工具调用: 缺少工具名称")
            
        return tool_name, tool_params
    
    @staticmethod
    async def execute_tool(tool_name: str, tool_params: Dict[str, Any]) -> ToolResult:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            tool_params: 工具参数字典
            
        Returns:
            工具执行结果
        """
        try:
            # 获取工具类
            tool_class = ToolRegistry.get(tool_name)
            tool_instance = tool_class()
            
            # 验证参数
            validated_params = tool_class.parameters(**tool_params)
            
            # 执行工具
            result = await tool_instance.run(validated_params)
            
            return result
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"工具执行失败: {str(e)}"
            )
    
    @staticmethod
    def format_tool_result_for_llm(tool_result: ToolResult) -> str:
        """
        将工具执行结果格式化为LLM可读的字符串
        
        Args:
            tool_result: 工具执行结果
            
        Returns:
            格式化的结果字符串
        """
        if tool_result.success:
            return f"工具执行成功:\n{json.dumps(tool_result.model_dump(), indent=2, ensure_ascii=False)}"
        else:
            return f"工具执行失败:\n错误: {tool_result.error}\n详细信息: {json.dumps(tool_result.model_dump(), indent=2, ensure_ascii=False)}"
    
    @staticmethod
    async def handle_tool_call(tool_call_data: Dict[str, Any]) -> str:
        """
        处理单次工具调用
        
        Args:
            tool_call_data: Claude 返回的工具调用数据
            
        Returns:
            格式化的工具执行结果
        """
        try:
            # 解析工具调用
            tool_name, tool_params = ToolExecutor.parse_tool_call(tool_call_data)
            
            # 执行工具
            result = await ToolExecutor.execute_tool(tool_name, tool_params)
            
            # 格式化结果
            return ToolExecutor.format_tool_result_for_llm(result)
            
        except Exception as e:
            return f"处理工具调用时出错: {str(e)}"
