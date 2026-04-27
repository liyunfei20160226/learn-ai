"""
Token 计数工具

提供简单但有效的 Token 估算功能，
不需要依赖外部的 tokenizer 库。
"""
import json
from typing import Any


def estimate_tokens(text: str) -> int:
    """
    估算文本的 Token 数量

    采用混合策略：
    - ASCII 字符：~4 chars = 1 token
    - 中文字符：~1.3 chars = 1 token
    - 其他 Unicode：~2 chars = 1 token

    Args:
        text: 待估算的文本

    Returns:
        估算的 Token 数量
    """
    if not text:
        return 0

    ascii_count = sum(1 for c in text if ord(c) < 128)
    chinese_count = sum(1 for c in text if 0x4e00 <= ord(c) <= 0x9fff)
    other_count = len(text) - ascii_count - chinese_count

    return int(
        ascii_count * 0.25 +
        chinese_count * 0.77 +
        other_count * 0.5
    )


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """
    估算单条消息的 Token 数量

    Args:
        message: Claude 格式的消息字典

    Returns:
        估算的 Token 数量
    """
    total = 0

    # 角色字段
    if "role" in message:
        total += estimate_tokens(message["role"])

    # 内容字段（可能是字符串或列表）
    content = message.get("content")
    if isinstance(content, str):
        total += estimate_tokens(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                total += estimate_tokens(block)
            elif isinstance(block, dict):
                if "text" in block:
                    total += estimate_tokens(block["text"])
                if "id" in block:
                    total += estimate_tokens(block["id"])
                if "name" in block:
                    total += estimate_tokens(block["name"])
                # 工具参数
                if "input" in block:
                    total += estimate_tokens(json.dumps(block["input"]))

    # 工具调用 ID（消息级别的）
    if "tool_use_id" in message:
        total += estimate_tokens(message["tool_use_id"])

    return total


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    """
    估算消息列表的总 Token 数量

    Args:
        messages: Claude 格式的消息列表

    Returns:
        估算的总 Token 数量
    """
    return sum(estimate_message_tokens(msg) for msg in messages)


class TokenBudget:
    """
    Token 预算管理器

    跟踪各层的 Token 使用情况，确保不超过总预算。
    """

    def __init__(self, total_budget: int = 150000):
        self.total_budget = total_budget
        self.allocations: dict[str, int] = {
            "system": 5000,
            "working": 50000,
            "tool_buffer": 80000,
            "short_term": 10000,
            "reserved": 5000,
        }

    def get_allocation(self, layer: str) -> int:
        """获取某层的 Token 预算"""
        return self.allocations.get(layer, 10000)

    def set_allocation(self, layer: str, budget: int) -> None:
        """设置某层的 Token 预算"""
        self.allocations[layer] = budget

    def get_available(self, used: int) -> int:
        """计算剩余可用的 Token 数"""
        return max(0, self.total_budget - used)

    def is_over_budget(self, used: int) -> bool:
        """检查是否超预算"""
        return used > self.total_budget
