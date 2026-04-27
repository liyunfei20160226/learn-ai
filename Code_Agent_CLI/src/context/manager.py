"""
ContextManager - 上下文管理统一门面

协调各上下文层，组装最终发送给 LLM 的完整上下文。
"""
from typing import Any, Optional

from .tool_buffer import ToolResultBufferLayer
from .working import WorkingMemoryLayer
from .token_counter import estimate_tokens


class ContextManager:
    """
    上下文管理器 - 统一管理所有上下文层

    Phase 1 实现：
    - WorkingMemoryLayer: 最近 10 轮对话
    - ToolResultBufferLayer: 工具结果分级截断
    """

    def __init__(
        self,
        total_budget: int = 150000,
        working_window_size: int = 10,
        working_max_tokens: int = 50000,
        tool_buffer_max_tokens: int = 80000,
        tool_small_threshold: int = 1000,
        tool_large_threshold: int = 5000,
    ):
        """
        初始化上下文管理器

        Args:
            total_budget: 总 Token 预算
            working_window_size: 工作记忆窗口大小（回合数）
            working_max_tokens: 工作记忆最大 Token 数
            tool_buffer_max_tokens: 工具结果缓冲最大 Token 数
            tool_small_threshold: 工具结果小阈值（字符数，以下完整保留）
            tool_large_threshold: 工具结果大阈值（字符数，以上深度截断）
        """
        self.total_budget = total_budget
        self.system_prompt: str = ""

        # 初始化各层
        self.working = WorkingMemoryLayer(
            window_size=working_window_size,
            max_tokens=working_max_tokens,
        )
        self.tool_buffer = ToolResultBufferLayer(
            max_total_tokens=tool_buffer_max_tokens,
            small_threshold=tool_small_threshold,
            large_threshold=tool_large_threshold,
        )

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self.system_prompt = prompt

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.working.add_user_message(content)

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """添加 Assistant 消息"""
        self.working.add_assistant_message(content, tool_calls)

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        添加工具执行结果

        工具结果不直接存入工作记忆，而是进入 ToolResultBuffer
        进行分级处理，然后在 build_context 时组装进去。

        Args:
            tool_call_id: 工具调用 ID
            tool_name: 工具名称
            result: 工具执行结果
            metadata: 元数据

        Returns:
            处理后的结果摘要（用于显示给用户）
        """
        return self.tool_buffer.add(tool_call_id, tool_name, result, metadata)

    def recall_tool_result(self, tool_call_id: str) -> Optional[str]:
        """召回某个工具结果的完整内容"""
        return self.tool_buffer.recall(tool_call_id)

    def build_context(self) -> list[dict[str, Any]]:
        """
        组装最终发送给 LLM 的完整上下文

        组装顺序：
        1. 工具结果（活跃的）
        2. 工作记忆（最近对话）

        注意：系统提示词由 LLMProvider 单独作为参数传入，
        不包含在这个消息列表中。

        Returns:
            Claude 格式的消息列表
        """
        messages: list[dict[str, Any]] = []

        # 工具结果放在前面（这样在上下文末尾的最新对话不受影响）
        # 但实际上工具结果应该和对应的工具调用相邻...
        # Phase 1 简化处理：直接把所有工具结果按时间顺序插到工作记忆中
        # 更精确的对齐需要更复杂的逻辑，Phase 2 再优化

        # 简化：工作记忆 + 工具结果都放进去
        # （实际上工作记忆中已经有 tool_use 了，tool_result 应该对应插入）
        # Phase 1 先用简单方案：直接把工具结果附加到工作记忆后面
        # 这不是最优的，但能工作，后续优化

        # 获取工作记忆
        messages.extend(self.working.get_messages())

        return messages

    def build_context_with_tool_results(self) -> list[dict[str, Any]]:
        """
        构建包含工具结果的完整上下文

        这是 build_context 的替代方案，会将工具结果显式插入到
        对应的 tool_use 之后。
        """
        # Phase 1 简化：直接拼接工具结果到最后
        # 更精确的对齐留到 Phase 2
        messages = self.build_context()
        messages.extend(self.tool_buffer.get_active_results())
        return messages

    def count_total_tokens(self) -> int:
        """估算完整上下文的 Token 总数"""
        system_tokens = estimate_tokens(self.system_prompt)
        working_tokens = self.working.count_tokens()
        tool_tokens = self.tool_buffer.count_tokens()
        return system_tokens + working_tokens + tool_tokens

    def stats(self) -> dict[str, Any]:
        """
        返回完整的 Token 使用统计

        Returns:
            {
                "total": 总 Token 数,
                "budget": 总预算,
                "layers": {
                    "system": {...},
                    "working": {...},
                    "tool_buffer": {...},
                }
            }
        """
        total = self.count_total_tokens()
        return {
            "total_tokens_used": total,
            "total_budget": self.total_budget,
            "remaining": self.total_budget - total,
            "utilization": f"{(total / self.total_budget * 100):.1f}%",
            "layers": {
                "system": {
                    "tokens": estimate_tokens(self.system_prompt),
                },
                "working": self.working.stats(),
                "tool_buffer": self.tool_buffer.stats(),
            },
        }

    def format_stats_for_display(self) -> str:
        """
        格式化统计信息，用于控制台显示

        Returns:
            人类可读的统计字符串
        """
        stats = self.stats()
        layers = stats["layers"]

        lines = [
            "📊 上下文使用统计",
            "=" * 40,
            f"  总 Token: {stats['total_tokens_used']:,} / {stats['total_budget']:,}",
            f"  使用率: {stats['utilization']}",
            "",
            f"  📝 系统提示词: {layers['system']['tokens']:,} tokens",
            f"  💬 工作记忆: {layers['working']['total_tokens']:,} tokens ({layers['working']['message_count']} 条消息)",
            f"  🔧 工具结果: {layers['tool_buffer']['total_tokens']:,} tokens ({layers['tool_buffer']['total_cached']} 个结果)",
            f"  📭 剩余可用: {stats['remaining']:,} tokens",
        ]

        # 显示最大的几个工具结果
        cached_tools = layers["tool_buffer"]["cached_tools"]
        if cached_tools:
            lines.append("")
            lines.append("  📦 已缓存的工具结果:")
            for tool in cached_tools[:5]:  # 最多显示 5 个
                lines.append(
                    f"    - {tool['tool_name']}: {tool['size_chars']:,} 字符 "
                    f"({tool['size_tokens']:,} tokens)"
                )
            if len(cached_tools) > 5:
                lines.append(f"    ... 还有 {len(cached_tools) - 5} 个")

        return "\n".join(lines)

    def clear(self) -> None:
        """清空所有上下文"""
        self.working.clear()
        self.tool_buffer.clear()

    def clear_tool_results(self) -> None:
        """只清空工具结果缓存"""
        self.tool_buffer.clear()
