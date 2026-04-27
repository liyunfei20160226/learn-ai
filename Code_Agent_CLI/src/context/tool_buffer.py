"""
工具结果缓冲层

专门管理大体积的工具结果，实现分级截断策略：
- 完整 (<1k chars): 原样保留
- 中等 (1k-5k chars): 保留前后 + 摘要
- 大型 (>5k chars): 仅元数据 + 可召回标记

这样可以避免一个大文件撑爆整个上下文。
"""
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import BaseLayer
from .token_counter import estimate_tokens


@dataclass
class CachedToolResult:
    """缓存的工具结果条目"""
    tool_call_id: str
    tool_name: str
    full_result: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0

    @property
    def size_chars(self) -> int:
        return len(self.full_result)

    @property
    def size_tokens(self) -> int:
        return estimate_tokens(self.full_result)


class ToolResultBufferLayer(BaseLayer):
    """
    工具结果缓冲层

    对工具执行结果进行分级管理，避免大结果撑爆上下文。
    """

    # 保留策略（字符数）
    KEEP_FIRST_CHARS = 800     # 深度截断时保留开头字符数
    KEEP_LAST_CHARS = 400      # 深度截断时保留末尾字符数
    MEDIUM_FIRST_CHARS = 1500  # 中等截断保留开头
    MEDIUM_LAST_CHARS = 800    # 中等截断保留末尾

    def __init__(
        self,
        max_total_tokens: int = 80000,
        max_results: int = 20,
        small_threshold: int = 1000,
        large_threshold: int = 5000,
    ):
        """
        初始化工具结果缓冲层

        Args:
            max_total_tokens: 工具结果总 Token 预算
            max_results: 最多保留的工具结果数量
            small_threshold: 小阈值（字符数，以下完整保留）
            large_threshold: 大阈值（字符数，以上深度截断）
        """
        self.max_total_tokens = max_total_tokens
        self.max_results = max_results
        self.THRESHOLD_FULL = small_threshold    # < N: 完整保留
        self.THRESHOLD_MEDIUM = large_threshold   # N-M: 中等截断 / >M: 深度截断
        self._cache: dict[str, CachedToolResult] = {}

    def add(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        添加工具结果，自动分级处理

        Args:
            tool_call_id: 工具调用 ID
            tool_name: 工具名称
            result: 工具执行的完整结果
            metadata: 元数据（如文件路径、执行时间等）

        Returns:
            处理后的结果摘要（用于显示给用户）
        """
        # 存入完整结果到缓存
        entry = CachedToolResult(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            full_result=result,
            metadata=metadata or {},
        )
        self._cache[tool_call_id] = entry

        # 如果超过最大数量，清理最旧的
        while len(self._cache) > self.max_results:
            oldest_id = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].timestamp
            )
            del self._cache[oldest_id]

        # 返回处理后的显示版本
        return self._format_for_display(entry)

    def recall(self, tool_call_id: str) -> Optional[str]:
        """
        召回某个工具结果的完整内容

        Args:
            tool_call_id: 工具调用 ID

        Returns:
            完整结果，如果不存在返回 None
        """
        entry = self._cache.get(tool_call_id)
        if entry:
            entry.access_count += 1
            return entry.full_result
        return None

    def get_active_results(self) -> list[dict[str, Any]]:
        """
        获取当前应该包含在上下文中的工具结果列表

        Returns:
            Claude 格式的工具结果消息列表
        """
        results = []
        total_tokens = 0

        # 按访问频率 + 时间排序（最近、最常访问的优先）
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda e: (-e.access_count, -e.timestamp)
        )

        for entry in sorted_entries:
            processed = self._process_entry(entry)
            # processed["content"] 是 [{"type": "tool_result", "content": "..."}] 格式
            processed_tokens = estimate_tokens(processed["content"][0]["content"])

            # 如果加上这个会超预算，就停止
            if total_tokens + processed_tokens > self.max_total_tokens:
                break

            results.append(processed)
            total_tokens += processed_tokens
            entry.access_count += 1

        return results

    def _process_entry(self, entry: CachedToolResult) -> dict[str, Any]:
        """
        根据结果大小分级处理工具结果

        Returns:
            Claude 格式的工具结果消息
        """
        size = entry.size_chars

        if size <= self.THRESHOLD_FULL:
            # 小结果：完整保留
            processed_content = entry.full_result

        elif size <= self.THRESHOLD_MEDIUM:
            # 中等结果：保留前后 + 截断标记
            first_part = entry.full_result[:self.MEDIUM_FIRST_CHARS]
            last_part = entry.full_result[-self.MEDIUM_LAST_CHARS:]
            truncated_count = size - self.MEDIUM_FIRST_CHARS - self.MEDIUM_LAST_CHARS
            processed_content = (
                f"{first_part}\n\n"
                f"... [已截断中间 {truncated_count} 字符，共 {size} 字符] ...\n\n"
                f"{last_part}"
            )

        else:
            # 大结果：深度截断，仅保留前后预览 + 可召回标记
            first_part = entry.full_result[:self.KEEP_FIRST_CHARS]
            last_part = entry.full_result[-self.KEEP_LAST_CHARS:]
            truncated_count = size - self.KEEP_FIRST_CHARS - self.KEEP_LAST_CHARS
            processed_content = (
                f"[工具结果已截断] 工具: {entry.tool_name}, 总大小: {size} 字符\n\n"
                f"{first_part}\n\n"
                f"... [已省略中间 {truncated_count} 字符] ...\n\n"
                f"{last_part}\n\n"
                f"[如需查看完整内容，请要求我展示此工具的完整结果]"
            )

        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": entry.tool_call_id,
                    "content": processed_content,
                }
            ],
        }

    def _format_for_display(self, entry: CachedToolResult) -> str:
        """
        格式化为控制台显示的版本（给用户看的）

        与上下文版本的区别：
        - 显示版本更简洁，主要用于状态提示
        - 上下文版本是给 LLM 看的，保留更多信息
        """
        size = entry.size_chars
        if size <= self.THRESHOLD_FULL:
            return f"完整结果 ({size} 字符)"
        elif size <= self.THRESHOLD_MEDIUM:
            return f"中等大小 ({size} 字符，已部分截断)"
        else:
            return f"大结果 ({size} 字符，已深度截断，可召回完整内容)"

    def count_tokens(self) -> int:
        """估算所有活跃结果的总 Token 数"""
        return sum(
            estimate_tokens(r["content"][0]["content"])
            for r in self.get_active_results()
        )

    def trim(self, target_tokens: int) -> int:
        """
        裁剪工具结果到目标 Token 数

        策略：优先裁剪最早、访问最少的结果
        """
        current_tokens = self.count_tokens()
        if current_tokens <= target_tokens:
            return 0

        trimmed = 0
        # 按优先级从低到高排序，优先移除最不重要的
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda e: (e.access_count, e.timestamp)
        )

        for entry in sorted_entries:
            if current_tokens - trimmed <= target_tokens:
                break
            # 实际上不移除，只是标记为不活跃？
            # 简化：先直接从缓存移除，以后可以优化为只降级
            entry_tokens = entry.size_tokens
            del self._cache[entry.tool_call_id]
            trimmed += entry_tokens

        return trimmed

    def clear(self) -> None:
        """清空所有缓存的工具结果"""
        self._cache.clear()

    def get_content(self) -> list[dict[str, Any]]:
        """实现 BaseLayer 接口：获取所有活跃的工具结果"""
        return self.get_active_results()

    def stats(self) -> dict[str, Any]:
        """返回统计信息"""
        return {
            "total_cached": len(self._cache),
            "total_tokens": self.count_tokens(),
            "max_tokens": self.max_total_tokens,
            "largest_result": max((e.size_chars for e in self._cache.values()), default=0),
            "cached_tools": [
                {
                    "tool_name": e.tool_name,
                    "size_chars": e.size_chars,
                    "size_tokens": e.size_tokens,
                    "access_count": e.access_count,
                }
                for e in self._cache.values()
            ],
        }
