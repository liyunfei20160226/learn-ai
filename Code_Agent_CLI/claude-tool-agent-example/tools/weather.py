"""
天气查询工具 - 示例工具实现
"""
from tools.base import BaseTool, ToolParameter, ToolResult
from pydantic import BaseModel


class WeatherParams(ToolParameter):
    """天气查询参数"""
    city: str
    """城市名称（如 "北京"、"上海"）"""


class WeatherResult(ToolResult):
    """天气查询结果"""
    city: str
    """城市名称"""
    temperature: float
    """温度（摄氏度）"""
    condition: str
    """天气状况（如 "晴天"、"多云"）"""
    humidity: int
    """湿度（百分比）"""
    wind_speed: float
    """风速（km/h）"""


class WeatherTool(BaseTool):
    """天气查询工具"""
    
    name = "weather"
    description = "查询指定城市的天气信息"
    parameters = WeatherParams
    returns = WeatherResult
    
    async def run(self, params: WeatherParams) -> WeatherResult:
        try:
            # 模拟天气 API 调用
            weather_data = {
                "北京": {
                    "temperature": 25,
                    "condition": "晴天",
                    "humidity": 45,
                    "wind_speed": 12.5
                },
                "上海": {
                    "temperature": 28,
                    "condition": "多云",
                    "humidity": 65,
                    "wind_speed": 15.0
                },
                "广州": {
                    "temperature": 32,
                    "condition": "小雨",
                    "humidity": 75,
                    "wind_speed": 10.0
                }
            }
            
            if params.city in weather_data:
                data = weather_data[params.city]
                return WeatherResult(
                    success=True,
                    city=params.city,
                    **data
                )
            else:
                return WeatherResult(
                    success=False,
                    city=params.city,
                    temperature=0,
                    condition="未知",
                    humidity=0,
                    wind_speed=0,
                    error=f"不支持查询 {params.city} 的天气"
                )
        except Exception as e:
            return WeatherResult(
                success=False,
                city=params.city,
                temperature=0,
                condition="未知",
                humidity=0,
                wind_speed=0,
                error=f"天气查询失败: {str(e)}"
            )
