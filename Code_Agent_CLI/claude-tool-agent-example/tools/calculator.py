"""
计算器工具 - 示例工具实现
"""
from tools.base import BaseTool, ToolParameter, ToolResult
from pydantic import BaseModel


class CalculatorParams(ToolParameter):
    """计算器工具参数"""
    expression: str
    """数学表达式（如 "2 + 3 * 4"）"""


class CalculatorResult(ToolResult):
    """计算器工具结果"""
    expression: str
    """计算的表达式"""
    result: float
    """计算结果"""


class CalculatorTool(BaseTool):
    """简单的计算器工具"""
    
    name = "calculator"
    description = "计算数学表达式的值"
    parameters = CalculatorParams
    returns = CalculatorResult
    
    async def run(self, params: CalculatorParams) -> CalculatorResult:
        try:
            # 安全的表达式计算
            import math
            result = eval(params.expression, {"__builtins__": {"math": math}}, {})
            
            return CalculatorResult(
                success=True,
                expression=params.expression,
                result=result
            )
        except Exception as e:
            return CalculatorResult(
                success=False,
                expression=params.expression,
                result=0.0,
                error=f"计算失败: {str(e)}"
            )
