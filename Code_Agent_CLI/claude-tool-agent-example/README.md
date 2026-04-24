# Claude 工具调用 Agent 示例

基于 Anthropic Claude 的 LLM Code Agent 工具调用完整实现示例。

## 功能概述

本示例展示了如何构建一个能够调用自定义工具的 LLM Agent，包括以下核心功能：

1. **工具注册机制** - 如何将 Python 函数/类注册为 LLM 可用工具
2. **工具调用解析** - 如何解析 LLM 返回的工具调用请求
3. **工具执行框架** - 如何安全地执行工具并返回结果给 LLM

## 架构组成

```
.
├── tools/                    # 工具实现目录
│   ├── base.py             # 工具基类定义
│   ├── calculator.py       # 计算器工具示例
│   └── weather.py          # 天气查询工具示例
├── agent/                   # Agent 核心模块
│   ├── tool_registry.py    # 工具注册中心
│   ├── tool_registry_initializer.py  # 工具初始化
│   └── tool_executor.py    # 工具执行器
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包
└── README.md               # 项目文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env` 并填入你的 Anthropic API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 3. 运行程序

```bash
python main.py
```

## 核心实现模式

### 1. 将 Python 函数注册为工具

#### 步骤：
1. 定义工具基类 `BaseTool` 规范接口
2. 实现具体工具类（如 `CalculatorTool`、`WeatherTool`）
3. 使用 `ToolRegistry` 注册所有工具

```python
from tools.base import BaseTool, ToolParameter, ToolResult
from pydantic import BaseModel


class CalculatorParams(ToolParameter):
    expression: str


class CalculatorResult(ToolResult):
    expression: str
    result: float


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "计算数学表达式的值"
    parameters = CalculatorParams
    returns = CalculatorResult
    
    async def run(self, params: CalculatorParams) -> CalculatorResult:
        # 实现工具逻辑
        pass
```

### 2. 解析 LLM 返回的工具调用请求

Claude API 会返回格式标准化的工具调用请求：

```json
{
  "type": "tool_use",
  "name": "calculator",
  "input": {"expression": "2 + 3 * 4"}
}
```

`ToolExecutor.parse_tool_call()` 方法负责解析这些请求：

```python
def parse_tool_call(tool_call_data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    tool_name = tool_call_data.get("name")
    tool_params = tool_call_data.get("parameters", {})
    return tool_name, tool_params
```

### 3. 执行工具并返回结果给 LLM

1. 根据工具名称获取对应的工具类
2. 验证并解析参数
3. 执行工具逻辑
4. 将结果格式化为 LLM 可读格式

```python
async def execute_tool(tool_name: str, tool_params: Dict[str, Any]) -> ToolResult:
    tool_class = ToolRegistry.get(tool_name)
    validated_params = tool_class.parameters(**tool_params)
    result = await tool_instance.run(validated_params)
    return result
```

## 工作流程

1. 用户输入问题
2. Agent 将问题发送给 Claude
3. Claude 判断是否需要调用工具
4. 如果需要，返回工具调用请求
5. 执行器解析并执行工具
6. 将工具结果返回给 Claude
7. Claude 根据结果生成最终回答
8. 重复直到得到最终答案

## 示例交互

```
=== Claude Code Agent 示例 ===
输入 'quit' 或 'exit' 退出程序

用户: 请计算 2 + 3 * 4 的结果

=== Claude 需要调用工具 ===
调用工具: calculator
工具参数: {'expression': '2 + 3 * 4'}

工具执行结果:
工具执行成功:
{
  "success": true,
  "data": {
    "expression": "2 + 3 * 4",
    "result": 14.0
  },
  "error": null
}

Claude: 计算结果是 14.0

--- 使用统计 ---
输入令牌: 256
输出令牌: 128

用户: 北京现在的天气怎么样？

=== Claude 需要调用工具 ===
调用工具: weather
工具参数: {'city': '北京'}

工具执行结果:
工具执行成功:
{
  "success": true,
  "data": {
    "city": "北京",
    "temperature": 25,
    "condition": "晴天",
    "humidity": 45,
    "wind_speed": 12.5
  },
  "error": null
}

Claude: 北京现在的天气是晴天，温度 25 摄氏度，湿度 45%，风速 12.5 km/h。

--- 使用统计 ---
输入令牌: 380
输出令牌: 95
```

## 扩展自定义工具

要添加新工具，只需：

1. 在 `tools/` 目录创建新的工具类
2. 继承 `BaseTool` 基类
3. 实现 `run()` 方法
4. 在 `agent/tool_registry_initializer.py` 中注册工具

```python
# tools/my_new_tool.py
from tools.base import BaseTool, ToolParameter, ToolResult
from pydantic import BaseModel


class MyToolParams(ToolParameter):
    param1: str
    param2: int


class MyToolResult(ToolResult):
    result: str


class MyNewTool(BaseTool):
    name = "my_new_tool"
    description = "我的新工具"
    parameters = MyToolParams
    returns = MyToolResult
    
    async def run(self, params: MyToolParams) -> MyToolResult:
        # 实现工具逻辑
        return MyToolResult(result=f"处理结果: {params.param1}, {params.param2}")
```

然后在 `tool_registry_initializer.py` 中注册：

```python
from tools.my_new_tool import MyNewTool

def initialize_tools():
    # ... 其他工具注册
    register_tool(MyNewTool)
```

## 关键特性

- **类型安全**：使用 Pydantic 进行参数验证
- **可扩展性**：轻松添加新工具
- **模块化设计**：清晰的分层架构
- **错误处理**：完善的异常捕获和结果返回
- **标准兼容**：遵循 Anthropic Claude 工具调用协议

## 生产环境注意事项

1. **安全**：
   - 避免使用 `eval()` 等不安全的函数
   - 对外部工具调用添加超时限制
   - 验证和过滤用户输入

2. **性能**：
   - 缓存工具结果（如果适用）
   - 实现工具调用的异步执行

3. **可观测性**：
   - 添加详细的日志
   - 监控工具调用频率和性能
   - 记录工具执行结果

4. **可靠性**：
   - 添加重试机制
   - 处理超时和网络错误
   - 实现健康检查
