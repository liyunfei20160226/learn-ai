"""
上下文管理子系统

提供分层、可扩展的上下文管理功能，包括：
- MemoryLayer: 回合级记忆管理 + 分层压缩
- ToolResultBufferLayer: 工具结果分级截断
- ContextManager: 统一门面
- CompressionLayer: 语义压缩层
"""
from .base import BaseLayer
from .manager import ContextManager
from .token_counter import TokenBudget, estimate_tokens, estimate_message_tokens, estimate_messages_tokens
from .tool_buffer import ToolResultBufferLayer
from .turn import TurnMemory
from .memory import MemoryLayer
from .compression import CompressionLayer, CompressedContent, CompressionStrategy
from .summarizer import Summarizer
from .session_manager import SessionManager

__all__ = [
    "BaseLayer",
    "ContextManager",
    "TokenBudget",
    "ToolResultBufferLayer",
    "TurnMemory",
    "MemoryLayer",
    "CompressionLayer",
    "CompressedContent",
    "CompressionStrategy",
    "Summarizer",
    "SessionManager",
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
]
