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
from typing import List, Dict, Any, Optional
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
    ) -> LLMResponse:
        """调用 OpenAI API"""
        kwargs = {
            "model": self.model,
            "messages": self._format_messages(messages),
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
