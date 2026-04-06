"""
需求分析师Agent - 分析模糊需求，主动提问逐步澄清
"""
import yaml
from typing import Dict
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..prompts import get_prompt


class RequirementsAnalystAgent(BaseAgent):
    """需求分析师Agent

    职责：
    1. 分析用户原始需求，识别模糊不明确的地方
    2. 以专业需求分析师角度，主动向用户提问，逐步澄清需求
    3. 每次提问后保存问答历史，支持断点续问
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def run(self, state: PipelineState) -> PipelineState:
        """生成下一个问题，或者判断是否已经足够清晰"""

        # 读取提示词模板
        prompt_template = get_prompt("requirements")

        # 构建完整prompt
        context = self._build_context(state)
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM生成问题
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析响应 - 期望格式: 问题列表或者 "ALL_CLEAR"
        parsed = self._parse_response(response_text)

        if parsed.get("all_clear"):
            # 所有问题已经澄清，不需要继续提问
            state.needs_more_questions = False
            return state

        # 添加新问题到问答历史
        for question in parsed.get("questions", []):
            state.requirements_qa_history.append({
                "question": question,
                "answer": None
            })

        state.needs_more_questions = True
        state.update_timestamp()

        return state

    def _build_context(self, state: PipelineState) -> str:
        """构建上下文"""
        lines = []
        lines.append("# 用户原始需求")
        lines.append(state.original_user_requirement)
        lines.append("")

        # 如果有质量闸门回流反馈，先告诉分析师问题在哪里
        if state.backflow_feedback:
            lines.append("# 质量闸门评审反馈")
            lines.append("质量闸门对之前生成的需求规格进行了评审，发现以下问题需要补充澄清：")
            lines.append("")
            lines.append(state.backflow_feedback)
            lines.append("")
            lines.append("请根据上述反馈，判断是否需要继续向用户提问以澄清这些问题。")
            lines.append("")

        lines.append("# 当前问答历史")
        lines.append("")

        for i, item in enumerate(state.requirements_qa_history, 1):
            q = item["question"]
            a = item["answer"]
            lines.append(f"## 第{i}轮")
            lines.append(f"**问题**: {q}")
            if a is not None:
                lines.append(f"**回答**: {a}")
            lines.append("")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> Dict:
        """解析响应"""
        # 尝试提取YAML
        try:
            # 查找YAML块
            if "```yaml" in response_text:
                start = response_text.find("```yaml") + 7
                end = response_text.find("```", start)
                yaml_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                yaml_text = response_text[start:end].strip()
            else:
                yaml_text = response_text.strip()

            data = yaml.safe_load(yaml_text)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError:
            pass

        # YAML解析失败，尝试文本解析
        if "ALL_CLEAR" in response_text or "所有问题" in response_text and "澄清" in response_text:
            return {"all_clear": True}

        # 提取问题，按行分割
        questions = []
        for line in response_text.splitlines():
            line = line.strip()
            if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")) and len(line) > 10:
                # 去掉列表标记
                q = line.lstrip("-* 1234567890.").strip()
                questions.append(q)

        if not questions:
            # 整段就是一个问题
            questions = [response_text[:200]]

        return {
            "all_clear": False,
            "questions": questions
        }