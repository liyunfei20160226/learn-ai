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
