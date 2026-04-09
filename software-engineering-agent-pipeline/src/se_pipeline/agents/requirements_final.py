"""
最终需求生成Agent - 问答澄清验证通过后，整理生成标准化需求规格文档
"""
import yaml
from datetime import datetime
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import RequirementsSpec, RequirementsQaHistory, QaHistoryItem
from ..prompts import get_prompt


class RequirementsFinalAgent(BaseAgent):
    """最终需求生成Agent

    在需求分析师和需求验证官完成多轮澄清验证通过后，
    将完整的问答整理成标准化的需求规格文档。
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def run(self, state: PipelineState) -> PipelineState:
        """生成最终需求规格文档"""

        # 读取提示词模板
        prompt_template = get_prompt("requirements_final")

        # 构建上下文
        context = self._build_context(state)
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM生成需求规格
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析YAML格式的需求规格
        parsed = self._parse_response(response_text)

        # 构建RequirementsSpec制品
        qa_history = self._build_qa_history(state)

        spec = RequirementsSpec(
            stage_id="requirements",
            project_id=state.project_id,
            timestamp=datetime.now(),
            data=RequirementsSpec.RequirementsData(**parsed),
            qa_history=qa_history,
            verification_passed=state.requirements_verification_passed,
        )

        # 保存到状态
        state.requirements_spec = spec
        state.update_timestamp()

        # 保存markdown文件到磁盘
        from ..storage.project_store import ProjectStore
        store = ProjectStore()
        store.save_requirements(state.project_id, spec)

        return state

    def _build_context(self, state: PipelineState) -> str:
        """构建上下文"""
        lines = []
        lines.append("# 项目信息")
        lines.append(f"项目名称: {state.project_name}")
        lines.append(f"用户原始需求: {state.original_user_requirement}")
        lines.append("")
        lines.append("# 完整问答澄清历史")

        for i, item in enumerate(state.requirements_qa_history, 1):
            q = item["question"]
            a = item["answer"]
            lines.append(f"## 第{i}轮问答")
            lines.append(f"**问题**: {q}")
            if a is not None:
                lines.append(f"**用户回答**: {a}")
            lines.append("")

        lines.append("# 任务")
        lines.append("请根据上面完整的问答历史，整理生成一份标准化的需求规格文档，输出YAML格式。")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> dict:
        """解析响应，提取YAML"""
        try:
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
            # 如果不是dict，YAML解析失败
            raise yaml.YAMLError("Parsed result is not a dict")
        except yaml.YAMLError:
            # 尝试修复常见问题
            cleaned = response_text
            # 去掉markdown
            for marker in ["```yaml", "```"]:
                cleaned = cleaned.replace(marker, "")
            cleaned = cleaned.strip()
            try:
                data = yaml.safe_load(cleaned)
                if isinstance(data, dict):
                    return data
                # 如果不是dict，YAML解析失败
                raise yaml.YAMLError("Parsed result is not a dict")
            except yaml.YAMLError:
                # 返回空结构
                return {
                    "title": "",
                    "description": "",
                    "requirements": [],
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "user_roles": [],
                    "out_of_scope": [],
                }

    def _build_qa_history(self, state: PipelineState) -> RequirementsQaHistory:
        """构建问答历史"""
        items = []
        remaining = []
        for i, item in enumerate(state.requirements_qa_history):
            qa_item = QaHistoryItem(
                question_id=f"q{i+1}",
                question=item["question"],
                answer=item["answer"],
            )
            items.append(qa_item)
            if item["answer"] is None:
                remaining.append(f"q{i+1}")

        return RequirementsQaHistory(
            items=items,
            all_questions_answered=len(remaining) == 0,
            remaining_questions=remaining,
        )
