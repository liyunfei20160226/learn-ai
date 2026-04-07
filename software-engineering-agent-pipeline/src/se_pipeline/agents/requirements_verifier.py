"""
需求验证官Agent - 独立验证需求是否足够清晰，发现遗漏则要求继续提问
"""
import yaml
from typing import Dict
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..prompts import get_prompt


class RequirementsVerifierAgent(BaseAgent):
    """需求验证官Agent

    职责：
    1. 独立重新阅读完整问答历史
    2. 判断是否所有关键问题都已澄清
    3. 如果发现遗漏或歧义，要求继续提问
    4. 确认全部澄清后，允许进入下一步
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def run(self, state: PipelineState) -> PipelineState:
        """验证需求是否足够清晰"""

        # 读取提示词模板
        prompt_template = get_prompt("requirements_verifier")

        # 构建上下文
        context = self._build_context(state)
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM进行验证
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析验证结果
        parsed = self._parse_response(response_text)

        # 更新状态
        state.requirements_verification_passed = parsed.get("all_clear", False)
        state.needs_more_questions = not state.requirements_verification_passed

        if not state.requirements_verification_passed:
            # 添加需要继续问的问题
            for question in parsed.get("additional_questions", []):
                state.requirements_qa_history.append({
                    "question": question,
                    "answer": None
                })

        state.update_timestamp()
        return state

    def _build_context(self, state: PipelineState) -> str:
        """构建上下文"""
        lines = []
        lines.append("# 用户原始需求")
        lines.append(state.original_user_requirement)
        lines.append("")

        # 如果有预处理的项目背景资料，加入上下文
        if state.project_background and state.documents_processed:
            # project_background 存储的是文件名，从文件读取内容
            from ..storage.project_store import ProjectStore
            store = ProjectStore()
            project_dir = store.get_project_dir(state.project_id)
            bg_file = project_dir / state.project_background
            if bg_file.exists():
                with open(bg_file, "r", encoding="utf-8") as f:
                    content = f.read()
                lines.append(content)
                lines.append("")

        # 如果有质量闸门回流反馈，先告诉验证官问题在哪里
        if state.backflow_feedback:
            lines.append("# 质量闸门评审反馈")
            lines.append("质量闸门对之前生成的需求规格进行了评审，发现以下问题需要补充澄清：")
            lines.append("")
            lines.append(state.backflow_feedback)
            lines.append("")
            lines.append("请根据上述反馈，结合完整问答历史，判断是否还有需要继续向用户澄清的问题。")
            lines.append("")

        lines.append("# 完整问答历史")
        lines.append("")

        unanswered = []
        for i, item in enumerate(state.requirements_qa_history, 1):
            q = item["question"]
            a = item["answer"]
            lines.append(f"## 问题 {i}")
            lines.append(f"**问题**: {q}")
            if a is not None:
                lines.append(f"**用户回答**: {a}")
            else:
                lines.append("**状态**: 尚未回答")
                unanswered.append((i, q))
            lines.append("")

        if unanswered:
            lines.append("# 当前待回答问题")
            for i, q in unanswered:
                lines.append(f"{i}. {q}")
            lines.append("")

        lines.append("# 任务")
        lines.append("请根据上面的问答历史，判断是否所有关键需求问题都已经得到了用户清晰回答。如果还有重要问题没有澄清，请列出需要继续问用户的问题。")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> Dict:
        """解析验证结果"""
        try:
            # 尝试提取YAML
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
            # 如果不是dict，YAML解析失败，走文本解析路径
            raise yaml.YAMLError("Parsed result is not a dict")
        except yaml.YAMLError:
            # 文本解析
            if "ALL_CLEAR" in response_text or "已经清晰" in response_text or "所有问题" in response_text and "澄清" in response_text:
                return {"all_clear": True, "additional_questions": []}

            # 提取额外问题
            questions = []
            for line in response_text.splitlines():
                line = line.strip()
                if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")) and len(line) > 10:
                    q = line.lstrip("-* 1234567890.").strip()
                    questions.append(q)

            return {
                "all_clear": len(questions) == 0,
                "additional_questions": questions
            }