"""
LLM Provider 抽象基类

定义所有 LLM Provider 必须实现的统一接口。
使用策略模式，不同 LLM（Claude、OpenAI）都实现同一个接口。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ToolCall:
    """LLM 返回的工具调用

    统一格式：不管是哪个 LLM 返回的，都解析成这个格式
    """
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """LLM 统一返回格式

    Attributes:
        text: 纯文本回答（如果没有工具调用的话）
        tool_calls: 工具调用列表（如果有）
        raw_response: 原始响应（用于调试）
    """
    text: str
    tool_calls: List[ToolCall]
    raw_response: Any


class LLMProvider(ABC):
    """LLM Provider 抽象基类

    所有具体的 LLM 提供商都必须实现这个接口。
    这样 Agent 就不需要关心具体是哪个 LLM，只需要调用统一的接口。
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称（用于日志显示）"""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        """
        对话补全（异步）

        Args:
            messages: 消息历史，Claude 格式：
                {"role": "user", "content": "..."}
                {"role": "assistant", "content": "..."}
            tools: 工具描述列表（JSON Schema 格式）
            system: 系统提示词（可选，作为单独参数传递给 LLM）

        Returns:
            LLMResponse: 统一格式的响应
        """
        pass
