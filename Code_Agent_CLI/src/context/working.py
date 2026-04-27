"""
工作记忆层

保留最近 N 轮完整对话，保证当前任务的上下文完整性。
超过窗口大小的回合会下沉到短期记忆层（目前先简化为直接丢弃）。
"""
from typing import Any, Optional

from .base import BaseLayer
from .token_counter import estimate_messages_tokens


class WorkingMemoryLayer(BaseLayer):
    """
    工作记忆层 - 滑动窗口保留最近 N 轮对话

    一轮对话定义为：用户消息 + (可选的) 工具调用 + (可选的) 工具结果 + Assistant 回复
    """

    def __init__(self, window_size: int = 10, max_tokens: int = 50000):
        """
        初始化工作记忆层

        Args:
            window_size: 保留的回合数
            max_tokens: 最大 Token 预算
        """
        self.window_size = window_size
        self.max_tokens = max_tokens
        self._messages: list[dict[str, Any]] = []

    def add(self, message: dict[str, Any]) -> None:
        """
        添加一条消息到工作记忆

        Args:
            message: Claude 格式的消息字典
        """
        self._messages.append(message)

        # 简单的滑动窗口：如果消息太多，删除最早的
        # （真正的回合识别比较复杂，Phase 1 先用消息数简化）
        while len(self._messages) > self.window_size * 3:  # 每回合约 3 条消息
            self._messages.pop(0)

        # Token 超限裁剪
        while self.count_tokens() > self.max_tokens:
            self._messages.pop(0)

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.add({"role": "user", "content": content})

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """添加 Assistant 消息"""
        if tool_calls:
            content_blocks = []
            if content:
                content_blocks.append({"type": "text", "text": content})
            for tc in tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            self.add({"role": "assistant", "content": content_blocks})
        else:
            self.add({"role": "assistant", "content": content})

    def get_messages(self) -> list[dict[str, Any]]:
        """获取所有消息"""
        return list(self._messages)

    def count_tokens(self) -> int:
        """估算所有消息的总 Token 数"""
        return estimate_messages_tokens(self._messages)

    def trim(self, target_tokens: int) -> int:
        """
        裁剪到目标 Token 数

        策略：FIFO，从最早的消息开始删
        """
        current_tokens = self.count_tokens()
        if current_tokens <= target_tokens:
            return 0

        trimmed = 0
        while self._messages and self.count_tokens() > target_tokens:
            removed = self._messages.pop(0)
            trimmed += estimate_messages_tokens([removed])

        return trimmed

    def clear(self) -> None:
        """清空工作记忆"""
        self._messages.clear()

    def get_content(self) -> list[dict[str, Any]]:
        """实现 BaseLayer 接口：获取所有消息"""
        return self.get_messages()

    def stats(self) -> dict[str, Any]:
        """返回统计信息"""
        return {
            "message_count": len(self._messages),
            "total_tokens": self.count_tokens(),
            "max_tokens": self.max_tokens,
            "window_size": self.window_size,
        }
