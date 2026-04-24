"""
工具注册初始化 - 集中注册所有可用工具
"""
from agent.tool_registry import register_tool
from tools.calculator import CalculatorTool
from tools.weather import WeatherTool


def initialize_tools():
    """初始化并注册所有工具"""
    # 注册计算器工具
    register_tool(CalculatorTool)
    
    # 注册天气查询工具
    register_tool(WeatherTool)
    
    print(f"已注册工具: {list(CalculatorTool.name, WeatherTool.name)}")


if __name__ == "__main__":
    initialize_tools()
