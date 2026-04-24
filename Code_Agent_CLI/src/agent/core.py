"""
Agent 核心 - 实现思考-行动循环

这是整个 Agent 系统的核心！
主要职责：
1. 维护消息历史（上下文）
2. 实现思考-行动循环
3. 调度工具调用

关键设计：依赖注入
- Agent 不直接依赖具体的 LLM（Claude、OpenAI）
- 而是依赖抽象的 LLMProvider 接口
- 这样可以轻松切换不同的 LLM，不需要改 Agent 代码
"""
import os
from typing import List, Dict, Any, Optional
from tools.registry import ToolRegistry
from tools.base import ToolError
from llm.base import LLMProvider, LLMResponse, ToolCall


class Agent:
    """
    Agent 核心类

    负责：
    - 保存对话历史
    - 思考：调用 LLM 分析，决定怎么做
    - 行动：如果需要，调用工具
    - 循环：直到得出最终答案

    依赖注入：通过构造函数传入 LLMProvider，而不是在内部直接创建
    """

    def __init__(self, llm_provider: LLMProvider, max_iterations: int = 5):
        """
        初始化 Agent

        Args:
            llm_provider: LLM 提供商实例（依赖注入）
            max_iterations: 最大工具调用轮数（防止无限循环）
        """
        self.llm = llm_provider
        self.max_iterations = max_iterations

        # 消息历史 - 只包含真正的对话，不包含 system prompt
        self.messages: List[Dict[str, Any]] = []

        # 系统提示词 - 单独保存，作为单独参数传给 LLM
        self.system_prompt: str = ""

        # 工具描述缓存（只生成一次）
        self._tool_descriptions: Optional[List[Dict[str, Any]]] = None

        # 加载系统提示词
        self._load_system_prompt()

    def _load_system_prompt(self):
        """
        从 prompts/system.md 加载系统提示词
        System prompt 不放在消息历史中，而是作为单独参数传给 LLM
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))  # agent/
        prompts_dir = os.path.join(os.path.dirname(current_dir), "prompts")  # prompts/
        system_prompt_path = os.path.join(prompts_dir, "system.md")

        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()

    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """
        获取所有已注册工具的描述，格式符合 Claude API 要求

        缓存机制：只在第一次调用时生成
        """
        if self._tool_descriptions is None:
            self._tool_descriptions = []
            for tool_name in ToolRegistry.list_names():
                tool = ToolRegistry.get(tool_name)
                self._tool_descriptions.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                })
        return self._tool_descriptions

    def add_user_message(self, content: str):
        """添加用户消息到历史"""
        self.messages.append({
            "role": "user",
            "content": content,
        })

    def add_tool_result_message(self, tool_use_id: str, content: str):
        """添加工具结果到历史"""
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": content,
                }
            ],
        })

    def add_assistant_message(self, content: str, tool_calls: Optional[List[ToolCall]] = None):
        """添加 Assistant 消息到历史"""
        if tool_calls:
            # 有工具调用的情况
            content_blocks = []
            if content:
                content_blocks.append({
                    "type": "text",
                    "text": content,
                })
            for tc in tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            self.messages.append({
                "role": "assistant",
                "content": content_blocks,
            })
        else:
            # 纯文本回答
            self.messages.append({
                "role": "assistant",
                "content": content,
            })

    async def think(self) -> Dict[str, Any]:
        """
        🧠 思考阶段 - 调用 LLM 分析历史，决定下一步做什么

        返回格式：
            {"action": "answer", "content": "..."}
            {"action": "tool", "tool_calls": [...], "content": "..."}
        """
        response: LLMResponse = await self.llm.chat_completion(
            messages=self.messages,
            tools=self.get_tool_descriptions(),
            system=self.system_prompt,
        )

        # 过滤不存在的工具（防止幻觉）
        valid_tool_calls = []
        available_tools = ToolRegistry.list_names()
        if response.tool_calls:
            for tc in response.tool_calls:
                if tc.name in available_tools:
                    valid_tool_calls.append(tc)
                else:
                    print(f"   ⚠️  模型尝试调用不存在的工具：'{tc.name}'（可用工具：{available_tools}）")

        if valid_tool_calls:
            return {
                "action": "tool",
                "tool_calls": valid_tool_calls,
                "content": response.text,
            }
        else:
            # 没有有效工具调用，直接回答
            return {
                "action": "answer",
                "content": response.text,
            }

    async def execute_tool(self, tool_call: ToolCall) -> str:
        """
        🔧 行动阶段 - 执行单个工具调用

        Args:
            tool_call: LLM 返回的工具调用对象

        Returns:
            工具执行结果
        """
        print(f"   [工具调用] 名称: {tool_call.name}, 参数: {tool_call.arguments}")

        try:
            tool = ToolRegistry.get(tool_call.name)
            result = await tool.run(tool_call.arguments)
            print(f"   [工具执行成功] 结果长度: {len(result)} 字符")
            return result

        except ToolError as e:
            error_msg = f"工具执行失败：{e}"
            print(f"   [工具错误] {error_msg}")
            return error_msg

        except Exception as e:
            error_msg = f"工具执行发生未知错误：{type(e).__name__}: {e}"
            print(f"   [工具异常] {error_msg}")
            return error_msg

    async def run(self, user_input: str) -> str:
        """
        🚀 运行一次完整的思考-行动循环

        Args:
            user_input: 用户最新的输入

        Returns:
            Agent 的最终回答
        """
        self.add_user_message(user_input)

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n[Agent 正在思考... 第 {iteration} 轮]")

            decision = await self.think()

            if decision["action"] == "answer":
                final_answer = decision["content"]
                self.add_assistant_message(final_answer)
                return final_answer

            elif decision["action"] == "tool":
                tool_calls = decision["tool_calls"]
                text_before = decision.get("content", "")

                # 先把 Assistant 的消息（包括工具调用）加入历史
                self.add_assistant_message(text_before, tool_calls)

                if text_before:
                    print(f"\n🤖 Agent: {text_before}")

                # 执行所有工具（支持并行调用，但这里顺序执行）
                for tool_call in tool_calls:
                    tool_result = await self.execute_tool(tool_call)
                    self.add_tool_result_message(tool_call.id, tool_result)

                # 循环回去继续思考
            else:
                error_msg = f"不知道要做什么: {decision}"
                self.add_assistant_message(error_msg)
                return error_msg

        return f"已达到最大工具调用次数 ({self.max_iterations})，停止执行。"
