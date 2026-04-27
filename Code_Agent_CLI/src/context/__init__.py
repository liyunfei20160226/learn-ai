"""
上下文管理子系统

提供分层、可扩展的上下文管理功能，包括：
- WorkingMemoryLayer: 最近 N 轮完整对话
- ToolResultBufferLayer: 工具结果分级截断
- ContextManager: 统一门面
"""
from .base import BaseLayer
from .manager import ContextManager
from .token_counter import TokenBudget, estimate_tokens, estimate_message_tokens, estimate_messages_tokens
from .tool_buffer import ToolResultBufferLayer
from .working import WorkingMemoryLayer

__all__ = [
    "BaseLayer",
    "ContextManager",
    "TokenBudget",
    "ToolResultBufferLayer",
    "WorkingMemoryLayer",
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
]
