"""
ContextManager - 上下文管理统一门面

协调各上下文层，组装最终发送给 LLM 的完整上下文。
"""
from typing import Any, Optional

from .tool_buffer import ToolResultBufferLayer
from .working import WorkingMemoryLayer
from .token_counter import estimate_tokens
from .compression import CompressionLayer, CompressionStrategy


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
        tool_small_threshold: int = 500,   # ⚡ 更激进的截断：小阈值 500 chars
        tool_large_threshold: int = 2000,  # ⚡ 更激进的截断：大阈值 2000 chars
        # Skill 阈值 - 操作手册需要尽量完整
        skill_small_threshold: int = 100000,
        skill_large_threshold: int = 100000,
        # Compression 层配置
        enable_compression: bool = True,
        llm_provider: Optional[Any] = None,
        compression_strategy: Optional[CompressionStrategy] = None,
    ):
        """
        初始化上下文管理器

        Args:
            total_budget: 总 Token 预算
            working_window_size: 工作记忆窗口大小（回合数）
            working_max_tokens: 工作记忆最大 Token 数
            tool_buffer_max_tokens: 工具结果缓冲最大 Token 数
            tool_small_threshold: 普通工具结果小阈值（字符数，以下完整保留）
            tool_large_threshold: 普通工具结果大阈值（字符数，以上深度截断）
            skill_small_threshold: Skill 小阈值（字符数，默认 100k，几乎不截断）
            skill_large_threshold: Skill 大阈值
            enable_compression: 是否启用智能压缩层
            llm_provider: LLM 提供商（用于摘要，不传则压缩层用简单截断）
            compression_strategy: 压缩策略配置
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
            skill_small_threshold=skill_small_threshold,
            skill_large_threshold=skill_large_threshold,
        )

        # Compression 层 - 智能压缩（Phase 6 新增）
        self.enable_compression = enable_compression
        self.compression: Optional[CompressionLayer] = None
        if enable_compression:
            self.compression = CompressionLayer(
                llm_provider=llm_provider,
                strategy=compression_strategy,
            )
            # 🔗 把压缩层引用传给 tool_buffer，用于触发后台异步摘要
            self.tool_buffer.set_compression_layer(self.compression)
        # 压缩统计
        self._compression_saved_chars: int = 0

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

    async def build_context_with_tool_results(self) -> list[dict[str, Any]]:
        """
        构建包含工具结果的完整上下文（支持压缩）

        🔧 消息格式修复（解决 HIGH 级别 Bug）：
        每条 tool_result 必须紧跟在对应的 tool_use 消息后面，而不是都放在末尾。
        """
        # 获取工作记忆中的消息
        messages = self.build_context()

        # Phase 6：压缩旧对话
        if self.enable_compression and self.compression:
            messages, saved_chars = await self.compression.process_old_messages(
                messages
            )
            self._compression_saved_chars += saved_chars

        # 获取工具结果
        tool_results_map: dict[str, dict[str, Any]] = {}
        for result in self.tool_buffer.get_active_results():
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                item = content[0]
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    tool_call_id = item.get("tool_use_id", "unknown")

                    # Phase 6：如果有缓存摘要，替换内容
                    if self.enable_compression and self.compression:
                        if self.compression.has_cached_summary(tool_call_id):
                            cached_summary = self.compression.get_cached_summary(tool_call_id)
                            if cached_summary:
                                item["content"] = cached_summary

                    tool_results_map[tool_call_id] = result

        # ✅ 修复：构建正确的消息序列
        # 遍历所有消息，遇到 tool_use 时在后面插入对应的 tool_result
        final_messages: list[dict[str, Any]] = []
        for msg in messages:
            final_messages.append(msg)

            # 如果这条消息包含 tool_use，在后面插入对应的 tool_result
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_id = block.get("id")
                        if tool_id in tool_results_map:
                            final_messages.append(tool_results_map[tool_id])
                            del tool_results_map[tool_id]  # 移除，避免重复

        # 剩下没有找到对应 tool_use 的工具结果，附加到末尾（兜底）
        for remaining_result in tool_results_map.values():
            final_messages.append(remaining_result)

        return final_messages

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

        compression_stats = None
        if self.compression:
            compression_stats = {
                "enabled": True,
                "total_compressed": self.compression.stats.total_compressed,
                "saved_chars": self.compression.stats.total_saved_chars,
                "saved_percent": self.compression.stats.overall_ratio,
                "items": [
                    {
                        "id": item.original_id,
                        "type": item.compression_type,
                        "original_size": item.original_size_chars,
                        "compressed_size": item.compressed_size_chars,
                        "ratio": item.saving_percent,
                    }
                    for item in self.compression.stats.compressed_items
                ],
            }
        else:
            compression_stats = {
                "enabled": False,
                "total_compressed": 0,
                "saved_chars": 0,
                "saved_percent": 0,
                "items": [],
            }

        return {
            "total_tokens_used": total,
            "total_budget": self.total_budget,
            "remaining": self.total_budget - total,
            "utilization": f"{(total / self.total_budget * 100):.1f}%",
            "compression": compression_stats,
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

        # Phase 6：显示压缩统计
        comp = stats["compression"]
        if comp["enabled"] and comp["total_compressed"] > 0:
            lines.append("")
            lines.append(
                f"  ✨ 智能压缩: 已压缩 {comp['total_compressed']} 项，"
                f"节省 {comp['saved_chars']:,} 字符 ({comp['saved_percent']:.1f}%)"
            )
            if comp["items"]:
                lines.append("     最近压缩项:")
                for item in comp["items"][-3:]:
                    lines.append(
                        f"       - [{item['type']}] {item['id'][:20]}: "
                        f"{item['original_size']:,} → {item['compressed_size']:,} "
                        f"({item['ratio']:.0f}%节省)"
                    )
                if len(comp["items"]) > 3:
                    lines.append(f"       ... 还有 {len(comp['items']) - 3} 项")
        elif comp["enabled"]:
            lines.append("")
            lines.append("  ✨ 智能压缩: 已启用，暂无压缩内容")

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
        if self.compression:
            self.compression.clear()

        # 同时清空全局压缩内容注册表
        from context.compression import clear_compressed_registry
        clear_compressed_registry()

    def clear_tool_results(self) -> None:
        """只清空工具结果缓存"""
        self.tool_buffer.clear()

    def recall_content(self, content_id: str) -> Optional[str]:
        """
        召回被压缩的内容的完整版本

        Args:
            content_id: 压缩时生成的内容 ID

        Returns:
            完整内容，如果找不到返回 None
        """
        if self.compression:
            return self.compression.recall_full_content(content_id)
        return None

    def list_compressed_items(self) -> list[str]:
        """列出所有被压缩的内容 ID"""
        if self.compression:
            return self.compression.list_compressed_ids()
        return []

    def toggle_compression(self, enabled: bool) -> None:
        """开关压缩功能"""
        self.enable_compression = enabled
        if not enabled and self.compression:
            # 关闭时清空压缩缓存
            self.compression.clear()
