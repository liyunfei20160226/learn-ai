"""
Compression 层 - 上下文智能压缩

与简单截断的区别：
- 不是简单地删除内容，而是用 LLM 生成语义摘要
- 保留核心语义，丢弃冗余信息
- 所有被压缩的内容都可以召回完整版本

重要设计：
- 全局压缩内容注册表：让 LLM 可以通过 Tool 自主召回完整内容
- LLM 看到的压缩摘要中包含提示，告诉它可以调用 recall_content 工具
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# ============= 全局压缩内容注册表 =============
# 让 RecallContentTool 可以访问到所有被压缩的内容
# 设计：CompressionLayer 压缩内容时自动注册，Tool 从这里取

_global_compressed_contents: dict[str, "CompressedContent"] = {}


def register_compressed_content(content: "CompressedContent") -> None:
    """注册被压缩的内容到全局注册表"""
    _global_compressed_contents[content.original_id] = content


def get_compressed_content(content_id: str) -> Optional["CompressedContent"]:
    """从全局注册表中获取被压缩的内容"""
    return _global_compressed_contents.get(content_id)


def list_all_compressed_ids() -> list[str]:
    """列出所有被压缩的内容 ID"""
    return list(_global_compressed_contents.keys())


def clear_compressed_registry() -> None:
    """清空全局注册表（用于测试或重置）"""
    _global_compressed_contents.clear()


@dataclass
class CompressionStrategy:
    """压缩策略配置"""
    # 工具结果压缩阈值（字符数）
    full_threshold: int = 1000           # 小于这个，完整保留，不压缩
    summarize_threshold: int = 5000       # 1k-5k 之间用 LLM 摘要
    hard_truncate_threshold: int = 20000  # 超过这个，直接硬截断（省 API 费用）

    # 压缩类型开关
    enable_llm_summarize: bool = True    # 是否启用 LLM 智能摘要

    # 对话压缩配置
    keep_latest_turns: int = 5          # 保留最近 N 轮不压缩


@dataclass
class CompressedContent:
    """单条压缩内容"""
    original_id: str           # 原始内容的唯一标识
    compression_type: str      # "summary" / "truncated" / "full"
    original_size_chars: int
    compressed_size_chars: int
    original_content: Optional[str]  # 完整内容（可召回）
    compressed_content: str    # 压缩后的内容
    content_type: str = "unknown"  # "tool_result" / "message"
    created_at: float = field(default_factory=time.time)
    access_count: int = 0

    @property
    def compression_ratio(self) -> float:
        """压缩率 = 压缩后 / 原始，值越小压缩越狠"""
        if self.original_size_chars == 0:
            return 1.0
        return self.compressed_size_chars / self.original_size_chars

    @property
    def saving_percent(self) -> float:
        """节省的百分比"""
        return (1 - self.compression_ratio) * 100


class CompressionStats:
    """压缩统计信息"""

    def __init__(self):
        self.total_compressed: int = 0
        self.total_original_chars: int = 0
        self.total_compressed_chars: int = 0
        self.compressed_items: list[CompressedContent] = []

    def add(self, item: CompressedContent) -> None:
        """添加一条压缩记录"""
        self.total_compressed += 1
        self.total_original_chars += item.original_size_chars
        self.total_compressed_chars += item.compressed_size_chars
        self.compressed_items.append(item)

    @property
    def total_saved_chars(self) -> int:
        return self.total_original_chars - self.total_compressed_chars

    @property
    def overall_ratio(self) -> float:
        if self.total_original_chars == 0:
            return 0.0
        return self.total_saved_chars / self.total_original_chars * 100

    def format_for_display(self) -> str:
        """格式化统计信息用于控制台显示"""
        if self.total_compressed == 0:
            return "  ✨ 压缩: 未启用或暂无压缩内容"

        lines = [
            f"  ✨ 已压缩 {self.total_compressed} 项内容",
            f"     总节省: {self.total_saved_chars:,} 字符 ({self.overall_ratio:.1f}%)",
        ]

        # 显示最近的几个压缩项
        for item in self.compressed_items[-3:]:
            lines.append(
                f"     - [{item.compression_type}] {item.original_id}: "
                f"{item.original_size_chars:,} → {item.compressed_size_chars:,} "
                f"({item.saving_percent:.0f}%)"
            )

        if len(self.compressed_items) > 3:
            lines.append(f"     ... 还有 {len(self.compressed_items) - 3} 项")

        return "\n".join(lines)


class CompressionLayer:
    """
    上下文压缩层

    在 ContextManager 组装上下文时，智能地压缩旧对话和大工具结果。

    工作流程：
    1. 评估哪些内容需要压缩
    2. 应用合适的压缩策略
    3. 保留完整内容在本地缓存（可召回）
    4. 返回压缩后的上下文给 LLM
    """

    def __init__(
        self,
        llm_provider: Any = None,
        strategy: Optional[CompressionStrategy] = None,
    ):
        from .summarizer import Summarizer

        self.strategy = strategy or CompressionStrategy()
        self.summarizer = Summarizer(llm_provider) if llm_provider else None
        self._pending_tasks: dict[str, asyncio.Task] = {}  # 后台摘要任务
        self.stats = CompressionStats()

    def has_cached_summary(self, tool_call_id: str) -> bool:
        """检查是否已有缓存的摘要（从全局注册表读取）"""
        entry = get_compressed_content(tool_call_id)
        return entry is not None and entry.compression_type != "full"

    def get_cached_summary(self, tool_call_id: str) -> Optional[str]:
        """获取缓存的摘要（从全局注册表读取）"""
        entry = get_compressed_content(tool_call_id)
        if entry and entry.compression_type != "full":
            return entry.compressed_content
        return None

    async def summarize_in_background(
        self,
        tool_name: str,
        tool_call_id: str,
        full_result: str,
    ) -> None:
        """
        后台异步生成摘要（不阻塞主流程）
        """
        # 已经有缓存了（从全局注册表检查）
        if get_compressed_content(tool_call_id) is not None:
            return

        # 检查是否已经在运行
        if tool_call_id in self._pending_tasks:
            return

        async def _task():
            try:
                await self.process_tool_result(tool_name, tool_call_id, full_result)
            except Exception:
                # 后台任务失败不影响主流程，静默处理
                pass
            finally:
                self._pending_tasks.pop(tool_call_id, None)

        task = asyncio.create_task(_task())
        self._pending_tasks[tool_call_id] = task

    async def process_tool_result(
        self,
        tool_name: str,
        tool_call_id: str,
        full_result: str,
    ) -> tuple[str, bool]:
        """
        处理工具结果，决定是否压缩

        Returns:
            (处理后的内容, 是否被压缩)
        """
        size = len(full_result)

        # 1. 小结果：完整保留
        if size <= self.strategy.full_threshold:
            return full_result, False

        # 2. 超大结果：直接硬截断，不尝试 LLM（节省 API 费用和时间）
        # ⚠️ 注意：recall_content 工具永远不截断，它的目的就是返回完整内容
        if size > self.strategy.hard_truncate_threshold and tool_name != "recall_content":
            first_part = full_result[:1000]
            last_part = full_result[-500:] if len(full_result) > 1500 else ""
            truncated_size = size - len(first_part) - len(last_part)

            truncated_content = (
                f"[内容已截断（超大结果）] 工具: {tool_name}\n"
                f"内容ID: {tool_call_id}\n"
                f"原始大小: {size:,} 字符\n"
                f"\n{first_part}\n\n"
                f"... [已省略中间 {truncated_size:,} 字符] ...\n\n"
                f"{last_part}\n\n"
                f"⚠️ 重要提示：因结果过大已直接截断。如需查看完整内容，请调用 recall_content 工具，\n"
                f'参数 content_id = "{tool_call_id}"'
            )

            truncated = CompressedContent(
                original_id=tool_call_id,
                compression_type="hard_truncated",
                original_size_chars=size,
                compressed_size_chars=len(truncated_content),
                original_content=full_result,
                compressed_content=truncated_content,
                content_type="tool_result",
            )
            self.stats.add(truncated)
            register_compressed_content(truncated)
            return truncated_content, True

        # 3. 中等结果：尝试 LLM 摘要
        if (
            self.strategy.enable_llm_summarize
            and self.summarizer
        ):
            try:
                summary = await self.summarizer.summarize_tool_result(
                    tool_name, full_result, tool_call_id  # 新增：传入 ID 供提示使用
                )
                compressed = CompressedContent(
                    original_id=tool_call_id,
                    compression_type="summary",
                    original_size_chars=size,
                    compressed_size_chars=len(summary),
                    original_content=full_result,
                    compressed_content=summary,
                    content_type="tool_result",
                )
                self.stats.add(compressed)
                register_compressed_content(compressed)  # ✅ 只写全局注册表
                return summary, True
            except Exception:
                # LLM 失败，回退到简单截断
                pass

        # 3. 大结果或 LLM 失败：硬截断
        first_part = full_result[:1000]
        last_part = full_result[-500:] if len(full_result) > 1500 else ""
        truncated_size = size - len(first_part) - len(last_part)

        truncated_content = (
            f"[内容已截断] 工具: {tool_name}\n"
            f"内容ID: {tool_call_id}\n"
            f"原始大小: {size:,} 字符\n"
            f"\n{first_part}\n\n"
            f"... [已省略中间 {truncated_size} 字符] ...\n\n"
            f"{last_part}\n\n"
            f"⚠️ 重要提示：以上是截断内容。如需查看完整内容，请调用 recall_content 工具，\n"
            f'参数 content_id = "{tool_call_id}"'
        )

        # 记录截断也作为压缩
        truncated = CompressedContent(
            original_id=tool_call_id,
            compression_type="truncated",
            original_size_chars=size,
            compressed_size_chars=len(truncated_content),
            original_content=full_result,
            compressed_content=truncated_content,
            content_type="tool_result",
        )
        self.stats.add(truncated)
        register_compressed_content(truncated)  # ✅ 只写全局注册表

        return truncated_content, True

    async def process_old_messages(
        self,
        messages: list[dict],
        keep_latest_n: Optional[int] = None,
    ) -> tuple[list[dict], int]:
        """
        压缩旧对话消息

        Args:
            messages: 完整消息列表
            keep_latest_n: 保留最近 N 轮不压缩，None 用配置值

        Returns:
            (处理后的消息列表, 节省的字符数)
        """
        if keep_latest_n is None:
            keep_latest_n = self.strategy.keep_latest_turns

        # 消息太少，不需要压缩
        if len(messages) <= keep_latest_n * 3:
            return messages, 0

        # 分割：新消息保留，旧消息压缩
        split_point = keep_latest_n * 3  # 每回合约 3 条消息
        new_messages = messages[-split_point:]
        old_messages = messages[:-split_point]

        if not old_messages:
            return messages, 0

        # 尝试用 LLM 摘要旧对话
        if self.summarizer and self.strategy.enable_llm_summarize:
            try:
                summary = await self.summarizer.summarize_conversation_turn(
                    old_messages
                )

                summary_id = f"conversation_summary_{int(time.time())}"
                original_size = sum(len(str(m)) for m in old_messages)

                compressed_message = {
                    "role": "user",
                    "content": (
                        "[之前对话摘要] 以下是本轮对话的早期内容摘要，完整内容已压缩：\n\n"
                        f"{summary}\n\n"
                        "[如需了解更多细节，可以要求召回完整对话历史]"
                    ),
                }

                compressed = CompressedContent(
                    original_id=summary_id,
                    compression_type="conversation_summary",
                    original_size_chars=original_size,
                    compressed_size_chars=len(str(compressed_message)),
                    original_content=str(old_messages),
                    compressed_content=summary,
                    content_type="conversation",
                )
                self.stats.add(compressed)
                register_compressed_content(compressed)

                result = [compressed_message] + new_messages
                saved_chars = original_size - len(str(compressed_message))
                return result, max(0, saved_chars)

            except Exception:
                    pass

        # 摘要失败或未启用 LLM，简单保留不压缩
        return messages, 0

    def recall_full_content(self, content_id: str) -> Optional[str]:
        """召回某个被压缩内容的完整版本（从全局注册表读取）"""
        entry = get_compressed_content(content_id)
        if entry:
            entry.access_count += 1
            return entry.original_content
        return None

    def list_compressed_ids(self) -> list[str]:
        """列出所有被压缩的内容 ID（从全局注册表读取）"""
        return list_all_compressed_ids()

    def clear(self) -> None:
        """清空压缩缓存（全局注册表是唯一存储）"""
        self.stats = CompressionStats()
        clear_compressed_registry()

