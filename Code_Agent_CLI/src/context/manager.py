"""
ContextManager - 上下文管理统一门面

协调各上下文层，组装最终发送给 LLM 的完整上下文。

Phase 7 架构：
- MemoryLayer: 回合级记忆管理 + 分层压缩
- ToolResultBufferLayer: 工具结果分级截断
- CompressionLayer: 语义压缩（被 MemoryLayer 调用）
- SessionManager: 全局会话持久化（对齐 Claude Code）
"""
from pathlib import Path
from typing import Any, Optional

from .tool_buffer import ToolResultBufferLayer
from .token_counter import estimate_tokens
from .compression import CompressionLayer, CompressionStrategy
from .memory import MemoryLayer
from .session_manager import SessionManager


class ContextManager:
    """
    上下文管理器 - 统一管理所有上下文层

    双模式运行：
    1. 旧模式（兼容）：使用简单的消息列表接口 add_user_message / add_assistant_message
    2. 新模式（推荐）：使用回合级生命周期 on_turn_start / record_tool_* / on_turn_end

    会话持久化：
    - 每轮对话结束后自动保存
    - 全局存储：~/.code-agent/sessions/
    - 用户可通过 /save 改名，/resume 继续上次，/load 加载任意历史
    """

    def __init__(
        self,
        total_budget: int = 150000,
        working_turns: int = 3,          # 工作区：最近 N 轮完整保留
        short_term_turns: int = 10,       # 短期记忆：N 轮内逐轮摘要
        tool_buffer_max_tokens: int = 80000,
        tool_small_threshold: int = 500,   # 更激进的截断
        tool_large_threshold: int = 2000,  # 更激进的截断
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
            working_turns: 工作区完整保留的回合数
            short_term_turns: 短期记忆区的回合数（超过的会被压缩）
            tool_buffer_max_tokens: 工具结果缓冲最大 Token 数
            tool_small_threshold: 普通工具结果小阈值
            tool_large_threshold: 普通工具结果大阈值
            skill_small_threshold: Skill 小阈值
            skill_large_threshold: Skill 大阈值
            enable_compression: 是否启用智能压缩层
            llm_provider: LLM 提供商（用于摘要）
            compression_strategy: 压缩策略配置
        """
        self.total_budget = total_budget
        self.system_prompt: str = ""
        self._next_turn_id: int = 1  # 下一个回合的 ID

        # Compression 层 - 智能压缩
        self.enable_compression = enable_compression
        self.compression: Optional[CompressionLayer] = None
        if enable_compression:
            self.compression = CompressionLayer(
                llm_provider=llm_provider,
                strategy=compression_strategy,
            )

        # 初始化各层
        self.memory = MemoryLayer(
            working_turns=working_turns,
            short_term_turns=short_term_turns,
            compression_layer=self.compression,
        )
        self.tool_buffer = ToolResultBufferLayer(
            max_total_tokens=tool_buffer_max_tokens,
            small_threshold=tool_small_threshold,
            large_threshold=tool_large_threshold,
            skill_small_threshold=skill_small_threshold,
            skill_large_threshold=skill_large_threshold,
        )
        if self.compression:
            self.tool_buffer.set_compression_layer(self.compression)

        # 压缩统计
        self._compression_saved_chars: int = 0

        # 会话管理
        self.session_manager = SessionManager()
        self.session_id = self.session_manager.generate_session_id()
        self.session_name: str = f"未命名会话_{self.session_id}"  # 用户可通过 /save 改名

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self.system_prompt = prompt

    # ============= 回合生命周期接口（新模式，推荐） =============

    def on_turn_start(self, user_query: str) -> int:
        """
        一回合开始

        Args:
            user_query: 用户原始问题

        Returns:
            turn_id: 回合 ID
        """
        turn_id = self._next_turn_id
        self.memory.on_turn_start(turn_id, user_query)
        self._next_turn_id += 1
        return turn_id

    def record_assistant_thinking(self, content: str) -> None:
        """记录 Assistant 的思考内容"""
        self.memory.record_assistant_thinking(content)

    def record_tool_call(self, tool_call_id: str, tool_name: str, arguments: dict) -> None:
        """记录工具调用"""
        self.memory.record_tool_call(tool_call_id, tool_name, arguments)

    def record_tool_result(self, tool_call_id: str, result: str) -> None:
        """记录工具结果"""
        self.memory.record_tool_result(tool_call_id, result)

    async def on_turn_end(self, final_answer: str) -> None:
        """
        一回合结束，触发压缩决策 + 自动持久化

        Args:
            final_answer: Assistant 最终回答
        """
        await self.memory.on_turn_end(final_answer)

        # 🚀 自动保存会话到文件（每轮结束后自动保存，不需要用户手动）
        # 用户不需要记住要 save，对话历史永远不会丢失
        self._auto_save_session()

    def _auto_save_session(self) -> None:
        """
        自动保存会话（内部调用）

        这是一个同步操作，因为保存的 JSON 通常很小，不会阻塞太久。
        如果会话有名称（用户用过 /save），就用那个名称，否则用 session_id。
        """
        try:
            self.session_manager.save_session(
                session_id=self.session_id,
                name=self.session_name,
                memory_data=self.memory.to_dict(),
                tool_buffer_data=self.tool_buffer.to_dict(),
                cwd=str(Path.cwd()),
            )
        except Exception:
            # 静默失败，保存失败不应该影响对话
            pass

    # ============= 会话管理公共接口 =============

    def rewind(self, turns: int = 1) -> int:
        """
        回退指定轮数的对话（时光机功能）

        场景：LLM 跑偏了 / 工具调用出错了 / 用户后悔说了某句话

        Args:
            turns: 要回退的轮数

        Returns:
            实际回退的轮数
        """
        actual = self.memory.rewind(turns)

        # 更新 next_turn_id：回退后的回合数 + 1
        self._next_turn_id = len(self.memory._turns) + 1

        # 回退后自动保存
        if actual > 0:
            self._auto_save_session()

        return actual

    def resume_last_session(self) -> bool:
        """
        继续上次的会话（/resume 命令）

        Returns:
            是否成功恢复
        """
        last_session_id = self.session_manager.get_last_session()
        if not last_session_id:
            return False

        return self.load_session(last_session_id)

    def save_session(self, name: str) -> str:
        """
        给当前会话起个好记的名字（/save 命令）

        注意：这不是保存，数据已经在每轮后自动保存了。
        这个命令只是改个名字，方便用户以后在列表里认出来。

        Args:
            name: 会话名称，比如 "分析项目架构"、"修复登录 bug"

        Returns:
            会话 ID
        """
        self.session_name = name
        self.session_manager.rename_session(self.session_id, name)
        return self.session_id

    def load_session(self, session_id: str) -> bool:
        """
        加载历史会话（/load 命令）

        Args:
            session_id: 会话 ID

        Returns:
            是否成功加载
        """
        data = self.session_manager.load_session(session_id)
        if not data:
            return False

        # 恢复会话 ID 和名称
        self.session_id = session_id
        self.session_name = data.get("name", f"已恢复会话_{session_id}")

        # 恢复 memory
        self.memory.from_dict(data)

        # 恢复 tool_buffer
        tool_buffer_data = data.get("tool_buffer_state", {})
        if tool_buffer_data:
            self.tool_buffer.from_dict(tool_buffer_data)

        # 更新 next_turn_id
        turns = data.get("turns", [])
        if turns:
            self._next_turn_id = max(t.get("turn_id", 0) for t in turns) + 1
        else:
            self._next_turn_id = 1

        return True

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        列出所有历史会话（/sessions 命令）

        Args:
            limit: 最多显示多少条

        Returns:
            按更新时间降序排列的会话列表
        """
        return self.session_manager.list_sessions(limit=limit)

    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话（/delete 命令）

        Args:
            session_id: 会话 ID

        Returns:
            是否成功删除
        """
        return self.session_manager.delete_session(session_id)

    # ============= 简单消息接口（旧模式，兼容） =============

    def add_user_message(self, content: str) -> None:
        """
        添加用户消息（旧接口兼容）

        注意：这会隐式创建一个新回合，但不支持压缩决策。
        建议使用 on_turn_start / on_turn_end 新模式。
        """
        self.on_turn_start(content)

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """
        添加 Assistant 消息（旧接口兼容）

        注意：这只是记录工具调用，不会结束回合。
        回合结束必须由调用者显式调用 on_turn_end()。
        """
        if tool_calls:
            for tc in tool_calls:
                self.record_tool_call(tc["id"], tc["name"], tc.get("arguments", {}))

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        添加工具执行结果（旧接口兼容）

        工具结果不直接存入工作记忆，而是进入 ToolResultBuffer
        进行分级处理，然后在 build_context 时组装进去。
        """
        # 记录到记忆层
        self.record_tool_result(tool_call_id, result)

        # 同时也记录到 tool_buffer（用于显示截断信息）
        return self.tool_buffer.add(tool_call_id, tool_name, result, metadata)

    # ============= 召回接口 =============

    def recall_tool_result(self, tool_call_id: str) -> Optional[str]:
        """召回某个工具结果的完整内容"""
        return self.tool_buffer.recall(tool_call_id)

    def recall_turn(self, turn_id: int) -> Optional[Any]:
        """召回某回合的完整记忆"""
        return self.memory.recall_turn(turn_id)

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

    # ============= 上下文构建接口 =============

    def build_context(self) -> list[dict[str, Any]]:
        """
        组装最终发送给 LLM 的完整上下文

        Returns:
            Claude 格式的消息列表
        """
        return self.memory.build_context()

    async def build_context_with_tool_results(self) -> list[dict[str, Any]]:
        """
        构建包含工具结果的完整上下文（支持压缩）

        🔧 消息格式修复：
        每条 tool_result 必须紧跟在对应的 tool_use 消息后面，而不是都放在末尾。
        """
        # 获取记忆层中的消息
        messages = self.build_context()

        # Phase 6：压缩旧对话（由 MemoryLayer 处理，这里保留 compression 层的处理作为补充）
        if self.enable_compression and self.compression:
            messages, saved_chars = await self.compression.process_old_messages(
                messages
            )
            self._compression_saved_chars += saved_chars

        # 获取工具结果，正确插入到消息序列中
        tool_results_map: dict[str, dict[str, Any]] = {}
        for result in self.tool_buffer.get_active_results():
            content = result.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                item = content[0]
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    tool_call_id = item.get("tool_use_id", "unknown")

                    # 如果有缓存摘要，替换内容
                    if self.enable_compression and self.compression:
                        if self.compression.has_cached_summary(tool_call_id):
                            cached_summary = self.compression.get_cached_summary(tool_call_id)
                            if cached_summary:
                                item["content"] = cached_summary

                    tool_results_map[tool_call_id] = result

        # ✅ 修复：构建正确的消息序列
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

    # ============= 统计接口 =============

    def count_total_tokens(self) -> int:
        """估算完整上下文的 Token 总数"""
        system_tokens = estimate_tokens(self.system_prompt)
        working_tokens = self.memory.count_tokens()
        tool_tokens = self.tool_buffer.count_tokens()
        return system_tokens + working_tokens + tool_tokens

    def stats(self) -> dict[str, Any]:
        """
        返回完整的 Token 使用统计

        Returns:
            {
                "total_tokens_used": 总 Token 数,
                "total_budget": 总预算,
                "memory": 记忆层统计,
                "compression": 压缩层统计,
                ...
            }
        """
        total = self.count_total_tokens()

        # 压缩层统计
        compression_stats = {"enabled": False, "total_compressed": 0, "saved_chars": 0}
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

        # 记忆层统计
        memory_stats = self.memory.stats()

        return {
            "total_tokens_used": total,
            "total_budget": self.total_budget,
            "remaining": self.total_budget - total,
            "utilization": f"{(total / self.total_budget * 100):.1f}%",
            "compression": compression_stats,
            "memory": memory_stats,
            "layers": {
                "system": {"tokens": estimate_tokens(self.system_prompt)},
                "memory": memory_stats,
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
        memory = stats["memory"]

        lines = [
            "📊 上下文使用统计",
            "=" * 40,
            f"  总 Token: {stats['total_tokens_used']:,} / {stats['total_budget']:,}",
            f"  使用率: {stats['utilization']}",
            "",
            f"  📝 系统提示词: {stats['layers']['system']['tokens']:,} tokens",
            f"  💬 记忆层: {memory['total_turns']} 轮对话",
            f"     - 工作区（完整）: {memory['working_turns']} 轮",
            f"     - 已压缩: {memory['compressed_turns']} 轮",
            f"     - 节省: {memory['saving_percent']:.1f}%",
            f"  🔧 工具结果: {stats['layers']['tool_buffer']['total_tokens']:,} tokens",
            f"  📭 剩余可用: {stats['remaining']:,} tokens",
        ]

        # 显示压缩统计
        comp = stats["compression"]
        if comp["enabled"] and comp["total_compressed"] > 0:
            lines.append("")
            lines.append(
                f"  ✨ 智能压缩: 已压缩 {comp['total_compressed']} 项，"
                f"节省 {comp['saved_chars']:,} 字符"
            )
            if comp["items"]:
                lines.append("     最近压缩项:")
                for item in comp["items"][-3:]:
                    lines.append(
                        f"       - [{item['type']}] {item['id'][:20]}: "
                        f"{item['original_size']:,} → {item['compressed_size']:,}"
                    )

        return "\n".join(lines)

    # ============= 管理接口 =============

    def clear(self) -> None:
        """清空所有上下文"""
        self.memory.clear()
        self.tool_buffer.clear()
        if self.compression:
            self.compression.clear()

        # 同时清空全局压缩内容注册表
        from context.compression import clear_compressed_registry

        clear_compressed_registry()

    def clear_tool_results(self) -> None:
        """只清空工具结果缓存"""
        self.tool_buffer.clear()

    def list_compressed_items(self) -> list[str]:
        """列出所有被压缩的内容 ID"""
        if self.compression:
            return self.compression.list_compressed_ids()
        return []

    def toggle_compression(self, enabled: bool) -> None:
        """开关压缩功能"""
        self.enable_compression = enabled
        if not enabled and self.compression:
            self.compression.clear()

    # 注意：旧的持久化接口已移除
    # 新的 SessionManager 接口：save_session(改名) / load_session(加载) / list_sessions / delete_session
