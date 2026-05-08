"""
RecallContentTool - 召回被压缩的完整内容

这是 Compression 层的配套工具：
- 当工具结果被智能压缩后，LLM 可以调用这个工具召回完整内容
- 不需要用户手动操作，LLM 自主判断是否需要看完整内容

设计思路：
1. CompressionLayer 压缩内容时，自动注册到全局注册表
2. 这个 Tool 从全局注册表中获取完整内容
3. LLM 在摘要中看到 "调用 recall_content" 的提示后，自主调用
"""
from typing import Any, Dict
from .base import BaseTool


class RecallContentTool(BaseTool):
    """
    召回被压缩内容的完整版本

    使用场景：
    - 当 LLM 看到工具结果被智能压缩后
    - 如果信息不够，可以调用此工具获取完整内容
    - 全程不需要用户干预
    """

    @property
    def name(self) -> str:
        return "recall_content"

    @property
    def description(self) -> str:
        return """召回被智能压缩的完整内容。
当你看到工具结果被标记为 [工具结果智能摘要] 并且信息不够用时，
调用此工具获取完整内容。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content_id": {
                    "type": "string",
                    "description": "被压缩内容的 ID，在摘要中标记为 '内容ID'",
                },
            },
            "required": ["content_id"],
        }

    async def run(self, arguments: Dict[str, Any]) -> str:
        """
        执行召回操作

        Args:
            arguments: {"content_id": "<ID>"}

        Returns:
            完整的内容，如果找不到返回错误提示
        """
        content_id = arguments.get("content_id", "")
        if not content_id:
            return "错误：缺少 content_id 参数"

        # 从全局注册表中获取
        from context.compression import get_compressed_content

        compressed = get_compressed_content(content_id)
        if not compressed:
            return f"错误：找不到 ID 为 '{content_id}' 的压缩内容"

        # 返回完整内容
        return f"""
[召回成功]
内容ID: {content_id}
原始大小: {compressed.original_size_chars:,} 字符
召回次数: {compressed.access_count + 1}

--- 完整内容 ---
{compressed.original_content}
""".strip()


class RecallTurnTool(BaseTool):
    """
    召回历史回合的完整内容

    这是 MemoryLayer 的配套工具：
    - 当旧回合被智能压缩后，LLM 可以调用这个工具召回完整内容
    - 不需要用户手动操作，LLM 自主判断是否需要看完整历史
    """

    @property
    def name(self) -> str:
        return "recall_turn"

    @property
    def description(self) -> str:
        return """召回某个历史对话回合的完整内容。
当你需要了解更早的对话细节（超过 3 轮前的对话）时，
调用此工具获取该回合的完整用户问题、工具调用、工具结果、最终回答。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "turn_id": {
                    "type": "integer",
                    "description": "回合 ID，从 1 开始递增，在摘要中标记为 '回合 N'",
                },
            },
            "required": ["turn_id"],
        }

    async def run(self, arguments: Dict[str, Any]) -> str:
        """
        执行召回操作

        Args:
            arguments: {"turn_id": 1}

        Returns:
            回合的完整内容
        """
        turn_id = arguments.get("turn_id", 0)
        if turn_id <= 0:
            return "错误：turn_id 必须大于 0"

        # 从全局 ContextManager 实例获取（通过全局注册表模式）
        # 注意：这里用懒加载，避免循环 import
        try:
            from main import get_agent  # type: ignore

            agent = get_agent()
            turn = agent.context.recall_turn(turn_id)
        except Exception:
            # 如果取不到全局 agent，用工具注册表中的上下文
            # 降级方案
            return f"错误：无法获取回合 {turn_id}，会话可能已重置"

        if not turn:
            return f"错误：找不到回合 ID 为 {turn_id} 的对话"

        # 格式化返回完整的回合内容
        result_lines = [
            f"[回合召回成功] 回合 {turn.turn_id}",
            f"重要性评分: {turn.importance_score}/10",
            f"被压缩: {'是' if turn.is_compressed else '否'}",
            f"召回次数: {turn.access_count}",
            "",
            "--- 用户问题 ---",
            turn.user_query,
            "",
            "--- Assistant 思考 ---",
            turn.assistant_thinking or "(无)",
            "",
        ]

        # 工具调用和结果
        if turn.tool_calls:
            result_lines.append("--- 工具调用 ---")
            for tc in turn.tool_calls:
                result_lines.append(f"工具: {tc['name']}")
                result_lines.append(f"参数: {tc['arguments']}")
                result_lines.append("")

            result_lines.append("--- 工具结果 ---")
            for tool_call_id, result in turn.tool_results.items():
                result_lines.append(f"[{tool_call_id}]")
                result_lines.append(str(result)[:500])
                if len(str(result)) > 500:
                    result_lines.append("... (结果过长，只显示前 500 字符)")
                result_lines.append("")

        result_lines.append("--- 最终回答 ---")
        result_lines.append(turn.final_answer or "(无最终回答)")

        return "\n".join(result_lines)
