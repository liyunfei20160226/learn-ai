"""
Summarizer - LLM 驱动的智能摘要生成器

特点：
1. 针对不同类型内容有不同的摘要策略
2. 保留关键语义，丢弃冗余信息
3. 摘要格式结构化，方便 LLM 后续理解
"""
import os
from typing import Any


class Summarizer:
    """LLM 驱动的智能摘要生成器"""

    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
        self._tool_summary_template = self._load_prompt_template("summarizer.md")
        self._conversation_summary_template = self._load_prompt_template("conversation_summary.md")

    def _load_prompt_template(self, filename: str) -> str:
        """加载摘要 prompt 模板"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(os.path.dirname(current_dir), "prompts")
        prompt_path = os.path.join(prompts_dir, filename)

        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()

        # Fallback: 如果文件不存在，返回基础模板
        return "请生成摘要，不超过 {max_chars} 字符：\n{content}"

    async def summarize_tool_result(
        self,
        tool_name: str,
        tool_result: str,
        content_id: str = "",
        max_chars: int = 1500,
    ) -> str:
        """
        摘要工具结果

        Args:
            tool_name: 工具名称
            tool_result: 完整的工具结果
            max_chars: 摘要最大字符数

        Returns:
            结构化的摘要内容，包含元数据标记
        """
        size = len(tool_result)

        # 小结果直接返回
        if size <= max_chars:
            return tool_result

        # 先截断输入，避免摘要本身太大
        truncated_input = tool_result[:8000] if len(tool_result) > 8000 else tool_result

        try:
            # 使用工具摘要模板构建 prompt
            prompt = self._tool_summary_template.format(
                tool_name=tool_name,
                size_chars=size,
                max_chars=max_chars,
                content=truncated_input
            )

            # 调用 LLM 生成摘要
            summary = await self._call_llm_simple(prompt)

            # 确保摘要不太长
            if len(summary) > max_chars:
                summary = summary[:max_chars - 3] + "..."

            # 添加元数据标记
            result = f"""
[工具结果智能摘要]
工具: {tool_name}
内容ID: {content_id}
原始大小: {size:,} 字符
摘要大小: {len(summary):,} 字符
压缩率: {len(summary)/size*100:.1f}%

--- 摘要内容 ---
{summary}

⚠️ 重要提示：以上是智能摘要。如需查看完整内容，请调用 recall_content 工具，
参数 content_id = "{content_id}"
"""
            return result.strip()

        except Exception as e:
            # 摘要失败，回退到简单截断
            first_part = tool_result[:1000]
            last_part = tool_result[-500:] if len(tool_result) > 1500 else ""
            return (
                f"[工具结果摘要失败，回退截断] 工具: {tool_name}, 错误: {e}\n\n"
                f"{first_part}\n\n... [中间省略] ...\n\n{last_part}"
            )

    async def summarize_conversation_turn(
        self,
        messages: list[dict],
        max_chars: int = 800,
    ) -> str:
        """
        摘要一轮或多轮对话

        Args:
            messages: 消息列表
            max_chars: 摘要最大字符数

        Returns:
            对话摘要
        """
        if not messages:
            return ""

        try:
            # 提取关键内容
            content_parts = []
            turn_count = 0
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                # 简化内容，避免太大
                if isinstance(content, list):
                    content_str = str(content)[:500]
                else:
                    content_str = str(content)[:500]

                content_parts.append(f"{role}: {content_str}")
                if role == "user":
                    turn_count += 1

            # 构建对话文本
            conversation_text = "\n".join(content_parts)

            # 使用对话摘要模板
            prompt = self._conversation_summary_template.format(
                turn_count=turn_count,
                start_turn=1,
                end_turn=turn_count,
                max_chars=max_chars,
                conversation_text=conversation_text
            )

            summary = await self._call_llm_simple(prompt)

            if len(summary) > max_chars:
                summary = summary[:max_chars - 3] + "..."

            return summary

        except Exception as e:
            return f"[对话摘要失败: {e}]"

    async def _call_llm_simple(self, prompt: str) -> str:
        """
        简单的 LLM 调用封装

        兼容不同的 LLM Provider 接口
        """
        try:
            # 尝试调用 simple_chat 方法（如果有）
            if hasattr(self.llm, "simple_chat"):
                return await self.llm.simple_chat(prompt)

            # 否则尝试标准的 chat_completion
            if hasattr(self.llm, "chat_completion"):
                response = await self.llm.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                )
                if hasattr(response, "text"):
                    return response.text
                if isinstance(response, dict):
                    return response.get("text", str(response))
                return str(response)

            # 都不行，直接返回简单截断
            return prompt[:500]

        except Exception:
            # 任何失败都回退到简单截断
            return prompt[:500]
