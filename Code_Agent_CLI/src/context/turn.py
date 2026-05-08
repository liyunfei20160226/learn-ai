"""
TurnMemory - 单回合记忆体

一整个回合的完整记忆 = 用户问 → Assistant 思考 → 工具调用 → 工具结果 → 最终回答
"""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TurnMemory:
    """
    一整个回合的记忆

    设计原则：
    1. 回合是最小的记忆单位，不拆散
    2. 压缩时整体压缩，保证语义完整性
    3. 所有原始内容都保留，可随时召回
    """

    turn_id: int
    user_query: str                          # 用户问题
    assistant_thinking: str                  # Assistant 的思考内容
    tool_calls: list[dict]                   # 工具调用列表
    tool_results: dict[str, str]             # 工具结果 {tool_call_id → content}
    final_answer: str                        # 最终回答

    # 压缩状态
    is_compressed: bool = False
    summary: Optional[str] = None            # 压缩后的摘要
    compressed_content_id: Optional[str] = None  # 关联到全局注册表的 ID

    # 元数据
    importance_score: int = 0                # 重要性评分（0-10，越高越晚压缩）
    created_at: float = field(default_factory=time.time)
    tokens_original: int = 0                 # 原始 Token 数
    tokens_compressed: int = 0               # 压缩后 Token 数
    access_count: int = 0                    # 被访问次数（用于 LRU）

    @property
    def compression_ratio(self) -> float:
        """压缩率 = 压缩后 / 原始，值越小压缩越狠"""
        if self.tokens_original == 0:
            return 1.0
        return self.tokens_compressed / self.tokens_original

    @property
    def saving_percent(self) -> float:
        """节省的百分比"""
        return (1 - self.compression_ratio) * 100

    def to_full_messages(self) -> list[dict]:
        """
        转换为完整的消息列表（用于未压缩的回合）

        按对话顺序重建：
        1. 用户消息
        2. Assistant 消息（含思考 + 工具调用）
        3. 工具结果（如果有）
        4. Assistant 最终回答
        """
        messages = []

        # 1. 用户消息
        messages.append({"role": "user", "content": self.user_query})

        # 2. Assistant 消息（思考 + 工具调用）
        if self.tool_calls:
            # 有工具调用的情况
            content_blocks = []
            if self.assistant_thinking:
                content_blocks.append({
                    "type": "text",
                    "text": self.assistant_thinking,
                })
            for tc in self.tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["arguments"],
                })
            messages.append({"role": "assistant", "content": content_blocks})

            # 3. 工具结果
            for tool_call_id, result in self.tool_results.items():
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result,
                    }],
                })

            # 4. 最终回答（如果有）
            if self.final_answer:
                messages.append({"role": "assistant", "content": self.final_answer})

        else:
            # 无工具调用，直接是 Assistant 回答
            if self.assistant_thinking or self.final_answer:
                content = self.assistant_thinking or self.final_answer
                messages.append({"role": "assistant", "content": content})

        return messages

    def to_summary_message(self) -> dict:
        """
        转换为摘要消息（用于已压缩的回合）

        只保留摘要，不暴露完整的长内容
        """
        if self.summary:
            content = (
                f"[回合 {self.turn_id} 摘要]\n"
                f"{self.summary}\n\n"
                f"[注：此回合已压缩，如需查看完整内容可调用 recall_turn({self.turn_id})]"
            )
        else:
            content = (
                f"[回合 {self.turn_id} 摘要]\n"
                f"用户问题：{self.user_query[:100]}...\n"
                f"[注：此回合已压缩，如需查看完整内容可调用 recall_turn({self.turn_id})]"
            )

        return {"role": "user", "content": content}

    def estimate_tokens(self) -> int:
        """
        估算这回合的原始 Token 数（大概值，用于预算管理）
        """
        total = len(self.user_query)
        total += len(self.assistant_thinking)
        total += len(self.final_answer)

        for tc in self.tool_calls:
            total += len(str(tc.get("arguments", "")))

        for result in self.tool_results.values():
            total += len(result)

        # 字符数 → Token 数粗略换算（中文约 1 字 = 1.5 Token，英文 4 字符 = 3 Token）
        # 这里用简单的 0.75 系数做估算
        return int(total * 0.75)
