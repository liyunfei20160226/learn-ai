"""
Layer 抽象基类

所有上下文管理层都继承自这个基类，
提供统一的 Token 计数、裁剪和清空接口。
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseLayer(ABC):
    """上下文管理层的抽象基类"""

    @abstractmethod
    def count_tokens(self) -> int:
        """
        估算当前层的 Token 使用量

        Returns:
            Token 数量（估算值）
        """
        pass

    @abstractmethod
    def trim(self, target_tokens: int) -> int:
        """
        裁剪内容到目标 Token 数

        Args:
            target_tokens: 目标 Token 数量

        Returns:
            实际裁剪掉的 Token 数量
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空该层的所有内容"""
        pass

    @abstractmethod
    def get_content(self) -> list[dict[str, Any]]:
        """
        获取该层应该包含在上下文中的内容

        Returns:
            消息列表，格式与 Claude API 一致
        """
        pass

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        简单的 Token 估算：1 token ≈ 4 个英文字符，或 1.3 个中文字符

        这是一个快速估算，不需要精确，用于预算控制。
        精确计数需要调用 LLM 的 tokenizer，但那会增加依赖和延迟。
        """
        # 简单估算：平均每个字符 0.3 tokens
        return int(len(text) * 0.3)
