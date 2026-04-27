"""
Claude Provider - Anthropic API 实现

这是最推荐的 Provider，因为 Claude 的工具调用设计最清晰，
和我们的消息格式完全兼容，不需要转换。
"""
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic
from .base import LLMProvider, LLMResponse, ToolCall


class ClaudeProvider(LLMProvider):
    """Claude LLM 提供商

    环境变量配置：
        ANTHROPIC_API_KEY: API Key（必需）
        ANTHROPIC_MODEL: 模型名称（可选，默认 claude-3-5-sonnet-20241022）
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY 环境变量未设置。\n"
                "请在 .env 文件中配置你的 API Key"
            )

        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "Claude"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """调用 Claude API

        Claude 的消息格式和我们内部格式完全一致！
        System prompt 作为单独的 system 参数传递。
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        # 解析响应
        text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw_response=response,
        )

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用 Claude API"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
        }

        if system:
            kwargs["system"] = system

        if tools:
            kwargs["tools"] = tools

        # Claude 流式 API：直接用最终消息（兼容不同 SDK 版本）
        # 流式过程中逐字符输出，结束时返回完整结果
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "content": text}

            # 消息结束，从最终消息获取工具调用
            message = await stream.get_final_message()
            for block in message.content:
                if block.type == "tool_use":
                    yield {
                        "type": "tool_call",
                        "tool_call": ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,
                        ),
                    }
