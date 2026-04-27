"""
OpenAI Provider - OpenAI 兼容格式实现

支持所有兼容 OpenAI API 格式的模型：
- OpenAI (GPT-4o, GPT-4, etc.)
- DeepSeek
- 通义千问
- 等等

注意：OpenAI 的消息格式和 Claude 略有不同，需要做转换。
"""
import os
import json
import warnings
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from .base import LLMProvider, LLMResponse, ToolCall


class OpenAIProvider(LLMProvider):
    """OpenAI 兼容 LLM 提供商

    环境变量配置：
        OPENAI_API_KEY: API Key（必需）
        OPENAI_MODEL: 模型名称（可选，默认 gpt-4o）
        OPENAI_BASE_URL: API 地址（可选，默认官方地址）
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY 环境变量未设置。\n"
                "请在 .env 文件中配置你的 API Key"
            )

        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        base_url = os.getenv("OPENAI_BASE_URL")

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换我们的内部消息格式（Claude 风格）为 OpenAI 格式

        主要差异：
        1. Claude 工具结果是 {"type": "tool_result", ...}
           OpenAI 工具结果是 {"role": "tool", "tool_call_id": "...", "content": "..."}
        2. Claude Assistant 消息工具调用是 {"type": "tool_use", ...}
           OpenAI 是 {"tool_calls": [...]}
        """
        result = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            # 工具结果消息
            if isinstance(content, list) and len(content) > 0 and content[0].get("type") == "tool_result":
                for tr in content:
                    result.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_use_id"],
                        "content": tr["content"],
                    })
                continue

            # Assistant 消息（可能带工具调用）
            if role == "assistant" and isinstance(content, list):
                text_content = ""
                tool_calls = []

                for block in content:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            }
                        })

                openai_msg: Dict[str, Any] = {"role": "assistant"}
                if text_content:
                    openai_msg["content"] = text_content
                if tool_calls:
                    openai_msg["tool_calls"] = tool_calls
                result.append(openai_msg)
                continue

            # 普通消息
            result.append({
                "role": role,
                "content": content,
            })

        return result

    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换工具描述为 OpenAI 格式"""
        result = []
        for tool in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                }
            })
        return result

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """调用 OpenAI API"""
        formatted_messages = self._format_messages(messages)

        # OpenAI 把 system 作为 role: "system" 的消息
        if system:
            formatted_messages.insert(0, {"role": "system", "content": system})

        kwargs = {
            "model": self.model,
            "messages": formatted_messages,
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)

        response = await self.client.chat.completions.create(**kwargs)

        # 解析响应
        choice = response.choices[0]
        text = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": tc.function.arguments}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
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
        """流式调用 OpenAI API

        先尝试真流式，失败则 fallback 到非流式（完整输出，不模拟）。
        某些兼容 OpenAI 的服务可能不完全支持流式。
        """
        formatted_messages = self._format_messages(messages)

        # OpenAI 把 system 作为 role: "system" 的消息
        if system:
            formatted_messages.insert(0, {"role": "system", "content": system})

        kwargs = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": True,
            "stream_options": {"include_usage": False},
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)

        tool_call_buffers = []

        # 抑制流式不支持产生的 RuntimeWarning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            try:
                # 尝试真流式
                async for chunk in self.client.chat.completions.create(**kwargs):
                    delta = chunk.choices[0].delta

                    # 文本内容
                    if delta.content:
                        yield {"type": "text", "content": delta.content}

                    # 工具调用
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            while len(tool_call_buffers) <= idx:
                                tool_call_buffers.append({
                                    "id": None,
                                    "name": "",
                                    "arguments": "",
                                })

                            if tc.id:
                                tool_call_buffers[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_call_buffers[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_call_buffers[idx]["arguments"] += tc.function.arguments

            except (TypeError, AttributeError, RuntimeError):
                # 真流式失败，fallback 到非流式，完整输出
                response = await self.chat_completion(messages, tools, system)
                yield {"type": "text", "content": response.text}  # 一次性输出
                for tc in response.tool_calls:
                    yield {"type": "tool_call", "tool_call": tc}
                return

        # 处理完整的工具调用
        for buf in tool_call_buffers:
            if buf["id"] and buf["name"]:
                try:
                    arguments = json.loads(buf["arguments"])
                except json.JSONDecodeError:
                    arguments = {"raw": buf["arguments"]}

                yield {
                    "type": "tool_call",
                    "tool_call": ToolCall(
                        id=buf["id"],
                        name=buf["name"],
                        arguments=arguments,
                    ),
                }
