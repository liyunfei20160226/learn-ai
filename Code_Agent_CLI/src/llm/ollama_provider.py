"""
Ollama Provider - 本地模型实现

实现 LLMProvider 抽象接口，通过 Ollama 调用本地模型。
支持 Llama 3、Qwen、Mistral、DeepSeek 等所有 Ollama 支持的模型。

注意：某些小模型（如 qwen2.5-coder:1.5b）可能不完全支持 tool_calls 协议，
工具调用效果取决于具体模型的能力。
"""
import os
import json
from typing import List, Dict, Any, Optional
from ollama import AsyncClient
from .base import LLMProvider, LLMResponse, ToolCall


class OllamaProvider(LLMProvider):
    """
    Ollama 本地 LLM 提供商

    环境变量配置：
        OLLAMA_MODEL: 模型名称（必需），例如 qwen2.5:7b, llama3.1:8b
        OLLAMA_HOST: Ollama 服务地址（可选，默认 http://localhost:11434）
    """

    def __init__(self):
        self._model = os.getenv("OLLAMA_MODEL")
        if not self._model:
            raise ValueError(
                "OLLAMA_MODEL 环境变量未设置。\n"
                "请设置为你想用的本地模型，例如: qwen2.5:7b, llama3.1:8b\n"
                "先运行 'ollama list' 查看已下载的模型"
            )

        host = os.getenv("OLLAMA_HOST")
        self.client = AsyncClient(host=host) if host else AsyncClient()

    @property
    def provider_name(self) -> str:
        return "Ollama"

    @property
    def model(self) -> str:
        return self._model

    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换我们的内部消息格式（Claude 风格）为 Ollama 要求的格式
        Ollama 使用和 OpenAI 类似的工具调用格式
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
                                "arguments": block["input"],
                            }
                        })

                ollama_msg: Dict[str, Any] = {"role": "assistant"}
                if text_content:
                    ollama_msg["content"] = text_content
                if tool_calls:
                    ollama_msg["tool_calls"] = tool_calls
                result.append(ollama_msg)
                continue

            # 普通消息
            result.append({
                "role": role,
                "content": content,
            })

        return result

    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换工具描述为 Ollama 格式（和 OpenAI 一样）"""
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
        """
        调用 Ollama 完成对话

        注意：工具调用能力取决于具体模型，有些小模型可能不支持官方 tool_calls 协议
        """
        kwargs = {
            "model": self._model,
            "messages": self._format_messages(messages),
        }

        if tools:
            kwargs["tools"] = self._format_tools(tools)

        response = await self.client.chat(**kwargs)

        # 解析响应
        message = response.message
        text = message.content or ""
        tool_calls = []

        # 标准模式：Ollama 返回的 tool_calls（大模型用）
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tc in message.tool_calls:
                arguments = tc.function.arguments
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {"raw": arguments}

                tool_calls.append(ToolCall(
                    id=tc.id or f"tool_{len(tool_calls)}",
                    name=tc.function.name,
                    arguments=arguments,
                ))

        # 对于不支持 tool_calls 的小模型，这里暂时不做特殊处理
        # 以后可以在这里加专门的解析逻辑

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw_response=response,
        )
