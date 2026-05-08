"""
MemoryLayer - 记忆层

职责：
1. 按回合管理对话历史
2. 决定什么时候压缩哪个回合
3. 组装发送给 LLM 的上下文
4. 支持召回被压缩的内容
5. 会话持久化

设计原则：
- 回合是最小记忆单位，不拆散
- 分层压缩：工作区（完整）→ 短期记忆（摘要）→ 长期记忆（全局摘要）
- 所有压缩内容都可召回，无损
"""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .base import BaseLayer
from .turn import TurnMemory
from .compression import CompressionLayer, CompressedContent
from .compression import register_compressed_content, clear_compressed_registry


class MemoryLayer(BaseLayer):
    """
    记忆层 - 对话生命周期管理

    分层策略：
    ┌─────────────────────────────────────────────────────────┐
    │  工作区（最近 N 轮）→ 100% 完整保留，不做任何压缩    │
    ├─────────────────────────────────────────────────────────┤
    │  短期记忆区（N~M 轮）→ 每轮做「回合级摘要」，保留核心  │
    ├─────────────────────────────────────────────────────────┤
    │  长期记忆区（> M 轮）→ 合并成「全局对话摘要」，仅要点  │
    └─────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        working_turns: int = 3,          # 工作区：最近 N 轮完整保留
        short_term_turns: int = 10,       # 短期记忆：N 轮内逐轮摘要
        compression_layer: Optional[CompressionLayer] = None,
    ):
        self.working_turns = working_turns
        self.short_term_turns = short_term_turns
        self.compression = compression_layer

        self._turns: list[TurnMemory] = []          # 所有回合（按时间排序）
        self._current_turn: Optional[TurnMemory] = None  # 正在进行的回合
        self._long_term_summary: Optional[str] = None  # 长期记忆的全局摘要

    # ============= 生命周期接口 =============

    def on_turn_start(self, turn_id: int, user_query: str) -> None:
        """
        一回合开始，初始化 TurnMemory

        Args:
            turn_id: 回合 ID（从 1 开始递增）
            user_query: 用户原始问题
        """
        self._current_turn = TurnMemory(
            turn_id=turn_id,
            user_query=user_query,
            assistant_thinking="",
            tool_calls=[],
            tool_results={},
            final_answer="",
        )

    def record_assistant_thinking(self, content: str) -> None:
        """
        记录 Assistant 的思考内容

        包括：流式输出的中间内容、思考过程等
        """
        if self._current_turn:
            self._current_turn.assistant_thinking += content

    def record_tool_call(self, tool_call_id: str, tool_name: str, arguments: dict) -> None:
        """
        记录一次工具调用
        """
        if self._current_turn:
            self._current_turn.tool_calls.append({
                "id": tool_call_id,
                "name": tool_name,
                "arguments": arguments,
            })

    def record_tool_result(self, tool_call_id: str, result: str) -> None:
        """
        记录工具执行结果
        """
        if self._current_turn:
            self._current_turn.tool_results[tool_call_id] = result

    async def on_turn_end(self, final_answer: str) -> None:
        """
        一回合结束，触发压缩决策

        核心决策逻辑：
        1. 计算这轮的重要性评分
        2. 加入记忆池
        3. 如果超过工作区大小，选择合适的旧回合进行压缩
        4. 如果超过短期记忆区大小，合并成长期记忆
        """
        if not self._current_turn:
            return

        # 记录最终回答
        self._current_turn.final_answer = final_answer

        # 估算原始 Token 数
        self._current_turn.tokens_original = self._current_turn.estimate_tokens()
        self._current_turn.tokens_compressed = self._current_turn.tokens_original

        # 计算重要性评分
        self._calculate_importance(self._current_turn)

        # 加入记忆池
        self._turns.append(self._current_turn)
        self._current_turn = None

        # ========== 压缩决策 ==========
        total_turns = len(self._turns)

        # 超过工作区大小，开始压缩最早的、重要性最低的回合
        if total_turns > self.working_turns:
            turn_to_compress = self._find_turn_to_compress()
            if turn_to_compress:
                await self._compress_turn(turn_to_compress)

        # 超过短期记忆区，合并最老的几轮成全局摘要
        if total_turns > self.short_term_turns:
            await self._merge_to_long_term()

    # ============= 压缩决策逻辑 =============

    def _calculate_importance(self, turn: TurnMemory) -> None:
        """
        计算回合的重要性评分（0-10）

        基于启发式规则：
        - 有工具调用 → +2
        - 有多次工具调用 → 每次 +1（最多 +3）
        - 回答很长（说明内容重要）→ +2
        - 用户问题有"bug"、"问题"、"错误"等关键词 → +2
        """
        score = 0

        # 有工具调用（说明在解决实际问题）
        if turn.tool_calls:
            score += 2
            score += min(len(turn.tool_calls), 3)  # 最多加 3

        # 回答很长（说明内容丰富）
        if len(turn.final_answer) > 500:
            score += 2

        # 用户问题中的关键词（说明是关键问题）
        important_keywords = ["bug", "错误", "问题", "修复", "解决", "为什么", "怎么"]
        query_lower = turn.user_query.lower()
        for kw in important_keywords:
            if kw in query_lower:
                score += 2
                break

        # 限制在 0-10 范围
        turn.importance_score = min(score, 10)

    def _find_turn_to_compress(self) -> Optional[TurnMemory]:
        """
        找到应该被压缩的回合

        选择策略：
        1. 只在非工作区的回合中选择
        2. 优先选择未压缩的
        3. 重要性评分最低的优先压缩
        4. 同样重要性的，更早的优先压缩
        """
        # 工作区 = 最后 N 轮，这些不压缩
        working_start = max(0, len(self._turns) - self.working_turns)
        candidates = self._turns[:working_start]

        # 过滤掉已经压缩的
        uncompressed = [t for t in candidates if not t.is_compressed]

        if not uncompressed:
            return None

        # 按重要性升序、时间升序排序（选最不重要、最早的）
        uncompressed.sort(key=lambda t: (t.importance_score, t.created_at))
        return uncompressed[0]

    async def _compress_turn(self, turn: TurnMemory) -> None:
        """
        压缩一个回合

        调用摘要层生成回合级摘要，标记为已压缩
        """
        if not self.compression or not self.compression.summarizer:
            # 没有摘要层，不做压缩，只标记
            turn.is_compressed = True
            turn.summary = f"回合 {turn.turn_id}: {turn.user_query[:100]}..."
            return

        try:
            # 把回合内容转换成消息列表，传给摘要器
            messages = turn.to_full_messages()
            summary = await self.compression.summarizer.summarize_conversation_turn(messages)

            turn.is_compressed = True
            turn.summary = summary
            turn.compressed_content_id = f"turn_{turn.turn_id}_summary"
            turn.tokens_compressed = int(len(summary) * 0.75)  # 估算摘要的 Token 数

        except Exception:
            # 摘要失败，回退到简单截断
            turn.is_compressed = True
            turn.summary = f"回合 {turn.turn_id}: {turn.user_query[:200]}..."
            turn.tokens_compressed = 200  # 估算

    async def _merge_to_long_term(self) -> None:
        """
        合并短期记忆区以外的所有回合成一个全局摘要

        这是最激进的压缩，只保留整个对话的核心脉络
        """
        if len(self._turns) <= self.short_term_turns:
            return

        # 最老的那些回合
        long_term_turns = self._turns[:-self.short_term_turns]

        if not long_term_turns:
            return

        # 简单版本：用第一回合的用户问题 + 回合数做一个全局摘要
        # TODO: 未来可以让摘要层生成真正的多回合合并摘要
        first_query = long_term_turns[0].user_query
        self._long_term_summary = (
            f"[长期记忆摘要]\n"
            f"共 {len(long_term_turns)} 轮对话（回合 1~{long_term_turns[-1].turn_id}）\n"
            f"对话起点：{first_query[:200]}...\n\n"
            f"[注：以上回合已深度压缩，如需查看具体某轮内容可调用 recall_turn(turn_id)]"
        )

    # ============= 上下文组装接口 =============

    def build_context(self) -> list[dict]:
        """
        组装发送给 LLM 的完整上下文

        顺序（从旧到新）：
        1. 长期记忆区：全局摘要（如果有）
        2. 短期记忆区：各回合摘要
        3. 工作记忆区：最近 N 轮完整内容
        """
        messages = []
        total_turns = len(self._turns)

        # 1. 长期记忆：全局摘要（> short_term_turns 的部分）
        if total_turns > self.short_term_turns and self._long_term_summary:
            messages.append({"role": "user", "content": self._long_term_summary})

        # 2. 短期记忆：各回合摘要（working_turns ~ short_term_turns 之间）
        if total_turns > self.working_turns:
            start = max(0, total_turns - self.short_term_turns)
            end = total_turns - self.working_turns

            for turn in self._turns[start:end]:
                if turn.is_compressed:
                    messages.append(turn.to_summary_message())
                else:
                    messages.extend(turn.to_full_messages())

        # 3. 工作记忆：最近 N 轮完整保留
        if total_turns > 0:
            for turn in self._turns[-self.working_turns:]:
                messages.extend(turn.to_full_messages())

        # 4. 当前正在进行的回合（还没结束，也要包含进去！
        # 否则第一回合的时候 _turns 是空的，_current_turn 才有用户的问题！
        if self._current_turn:
            messages.append({
                "role": "user",
                "content": self._current_turn.user_query,
            })

        return messages

    # ============= 召回接口 =============

    def recall_turn(self, turn_id: int) -> Optional[TurnMemory]:
        """
        召回某一轮的完整内容

        即使被压缩了，也能拿到完整的原始内容
        """
        for turn in self._turns:
            if turn.turn_id == turn_id:
                turn.access_count += 1
                return turn
        return None

    def rewind(self, turns: int = 1) -> int:
        """
        回退指定轮数的对话（时光机功能）

        场景：LLM 跑偏了 / 工具调用出错了 / 用户后悔说了某句话

        Args:
            turns: 要回退的轮数

        Returns:
            实际回退的轮数
        """
        if turns <= 0:
            return 0

        total_turns = len(self._turns)
        if total_turns == 0:
            return 0

        # 实际能回退的轮数不能超过现有回合数
        actual_rewind = min(turns, total_turns)

        # 删除最后 n 个 TurnMemory
        del self._turns[-actual_rewind:]

        # 重新计算压缩状态：回退后可能某些回合不需要压缩了
        # 把所有非工作区的回合重置为未压缩，让它们重新显示完整内容
        remaining = len(self._turns)
        if remaining > self.working_turns:
            # 短期记忆区的回合，重置压缩状态
            for turn in self._turns[self.working_turns:]:
                turn.is_compressed = False
                turn.summary = None
                turn.compressed_content_id = None
        else:
            # 回退后所有回合都在工作区，全部不压缩
            for turn in self._turns:
                turn.is_compressed = False
                turn.summary = None
                turn.compressed_content_id = None

        # 如果所有回合都在短期记忆区内，清除长期记忆摘要
        if len(self._turns) <= self.short_term_turns:
            self._long_term_summary = None

        return actual_rewind

    # ============= 统计接口 =============

    def stats(self) -> dict:
        """
        获取记忆统计信息
        """
        total_compressed = sum(1 for t in self._turns if t.is_compressed)
        original_tokens = sum(t.tokens_original for t in self._turns)
        compressed_tokens = sum(
            t.tokens_compressed if t.is_compressed else t.tokens_original
            for t in self._turns
        )

        saving_percent = 0.0
        if original_tokens > 0:
            saving_percent = (1 - compressed_tokens / original_tokens) * 100

        return {
            "total_turns": len(self._turns),
            "compressed_turns": total_compressed,
            "working_turns": min(self.working_turns, len(self._turns)),
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saving_percent": saving_percent,
            "has_long_term": self._long_term_summary is not None,
        }

    def get_content(self) -> list[dict]:
        """
        实现 BaseLayer 接口：获取上下文内容
        """
        return self.build_context()

    def count_tokens(self) -> int:
        """
        实现 BaseLayer 接口：估算上下文的总 Token 数
        """
        total = 0

        # 长期记忆摘要
        if self._long_term_summary:
            total += int(len(self._long_term_summary) * 0.75)

        # 各回合
        for turn in self._turns:
            if turn.is_compressed:
                total += turn.tokens_compressed
            else:
                total += turn.tokens_original

        return total

    def trim(self, target_tokens: int) -> int:
        """
        实现 BaseLayer 接口：裁剪到目标 Token 数

        策略：从最老的回合开始，先压缩，实在不行就删除
        """
        current = self.count_tokens()
        if current <= target_tokens:
            return 0

        trimmed = 0

        # 先尝试压缩所有未压缩的非工作区回合
        for turn in self._turns[:-self.working_turns]:
            if not turn.is_compressed:
                # 压缩会减少 Token，这里简单估算
                saved = turn.tokens_original - turn.tokens_compressed
                turn.is_compressed = True
                trimmed += saved
                if current - trimmed <= target_tokens:
                    return trimmed

        # 压缩完还是超，删除最老的回合
        while self._turns and self.count_tokens() > target_tokens:
            removed = self._turns.pop(0)
            trimmed += removed.tokens_compressed if removed.is_compressed else removed.tokens_original

        return trimmed

    def clear(self) -> None:
        """
        清空所有记忆
        """
        self._turns.clear()
        self._current_turn = None
        self._long_term_summary = None

    # ============= 持久化接口 =============

    def to_dict(self) -> dict:
        """
        序列化到字典（供 SessionManager 使用）
        """
        return {
            "working_turns": self.working_turns,
            "short_term_turns": self.short_term_turns,
            "long_term_summary": self._long_term_summary,
            "turns": [asdict(t) for t in self._turns],
        }

    def from_dict(self, data: dict) -> None:
        """
        从字典反序列化（供 SessionManager 使用）
        """
        # 清空现有状态
        self.clear()
        clear_compressed_registry()

        # 恢复配置
        self.working_turns = data["working_turns"]
        self.short_term_turns = data["short_term_turns"]
        self._long_term_summary = data.get("long_term_summary")

        # 恢复回合
        for turn_data in data["turns"]:
            # 从 dict 重建 TurnMemory
            turn = TurnMemory(
                turn_id=turn_data["turn_id"],
                user_query=turn_data["user_query"],
                assistant_thinking=turn_data["assistant_thinking"],
                tool_calls=turn_data["tool_calls"],
                tool_results=turn_data["tool_results"],
                final_answer=turn_data["final_answer"],
            )
            turn.is_compressed = turn_data["is_compressed"]
            turn.summary = turn_data.get("summary")
            turn.compressed_content_id = turn_data.get("compressed_content_id")
            turn.importance_score = turn_data.get("importance_score", 0)
            turn.created_at = turn_data.get("created_at", 0)
            turn.tokens_original = turn_data.get("tokens_original", 0)
            turn.tokens_compressed = turn_data.get("tokens_compressed", 0)
            turn.access_count = turn_data.get("access_count", 0)

            # 如果有压缩内容，注册到全局注册表
            if turn.is_compressed and turn.compressed_content_id:
                # 设计决策：回合原始内容存储在 TurnMemory 中
                # 不需要在 CompressedContent 中重复存储
                # recall_turn() 直接从 TurnMemory 返回完整内容
                compressed = CompressedContent(
                    original_id=turn.compressed_content_id,
                    compression_type="turn_summary",
                    original_size_chars=turn.tokens_original,
                    compressed_size_chars=turn.tokens_compressed,
                    original_content=None,
                    compressed_content=turn.summary or "",
                )
                register_compressed_content(compressed)

            self._turns.append(turn)

    def save_session(self, path: str) -> None:
        """
        保存整个会话到文件（旧接口兼容，推荐用 SessionManager）

        Args:
            path: 保存路径，建议用 .session.json 后缀
        """
        data = self.to_dict()
        data["version"] = 1

        # 保存到文件
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, path: str) -> None:
        """
        从文件加载会话（旧接口兼容，推荐用 SessionManager）

        Args:
            path: 会话文件路径
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 验证版本
        if data.get("version") != 1:
            raise ValueError(f"Unsupported session version: {data.get('version')}")

        self.from_dict(data)

        # 注意：next_turn_id 存在 ContextManager 中，调用方需要负责恢复
