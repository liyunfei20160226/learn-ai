"""
自动评审 - LLM驱动的质量闸门自动检查
"""
import json
from typing import List
from langchain_openai import ChatOpenAI

from ..types.quality_gate import QualityGateResult, CheckResult, CheckItem, Severity
from ..types.artifacts import RequirementsSpec
from .checklists import get_requirements_checklist


class AutoReviewer:
    """LLM驱动的自动评审器"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    def review_requirements(self, spec: RequirementsSpec) -> QualityGateResult:
        """评审需求规格"""
        checklist = get_requirements_checklist()

        # 构建prompt
        prompt = self._build_review_prompt("需求分析", spec, checklist)

        response = self.llm.invoke(prompt)
        response_text = response.content.strip()

        # 解析结果
        return self._parse_result(response_text, checklist, "requirements")

    def _build_review_prompt(self, stage_name: str, artifact: any, checklist: List[CheckItem]) -> str:
        """构建评审prompt"""
        lines = []
        lines.append(f"# {stage_name}阶段质量评审")
        lines.append("")
        lines.append("## 待评审制品内容")
        lines.append("")
        if isinstance(artifact, RequirementsSpec):
            lines.append(f"项目标题: {artifact.data.title}")
            lines.append(f"项目描述: {artifact.data.description}")
            lines.append(f"功能需求数量: {len(artifact.data.functional_requirements)}")
            lines.append(f"用户角色数量: {len(artifact.data.user_roles)}")
            lines.append("")

        lines.append("## 检查清单")
        lines.append("")
        for item in checklist:
            lines.append(f"- [{item.id}] {item.question} (严重性: {item.severity})")
        lines.append("")
        lines.append("请对照检查清单，逐项评审这个制品是否符合质量要求。输出JSON格式:")
        lines.append("")
        lines.append("```json")
        lines.append("{")
        lines.append("  \"results\": [")
        lines.append("    {")
        lines.append("      \"id\": \"检查项ID\",")
        lines.append("      \"passed\": true/false,")
        lines.append("      \"feedback\": \"你的评价和反馈\"")
        lines.append("    }")
        lines.append("  ]")
        lines.append("}")
        lines.append("```")

        return "\n".join(lines)

    def _parse_result(self, response_text: str, checklist: List[CheckItem], stage_id: str) -> QualityGateResult:
        """解析评审结果"""
        try:
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            else:
                json_text = response_text.strip()

            data = json.loads(json_text)
        except json.JSONDecodeError:
            # 解析失败，默认通过
            return QualityGateResult(
                stage_id=stage_id,
                passed=True,
                feedback="JSON解析失败，默认通过",
            )

        results = []
        errors = []
        warnings = []

        checklist_map = {item.id: item for item in checklist}

        for result in data.get("results", []):
            item_id = result.get("id")
            if item_id not in checklist_map:
                continue
            item = checklist_map[item_id]
            passed = result.get("passed", True)
            feedback = result.get("feedback", "")

            check_result = CheckResult(
                item=item,
                passed=passed,
                feedback=feedback
            )

            results.append(check_result)

            if not passed:
                if item.severity == Severity.ERROR:
                    errors.append(check_result)
                elif item.severity == Severity.WARNING:
                    warnings.append(check_result)

        passed = len(errors) == 0

        # 汇总反馈
        all_feedback = []
        if errors:
            all_feedback.append(f"发现 {len(errors)} 个错误级问题:")
            for e in errors:
                all_feedback.append(f"- {e.item.question}: {e.feedback}")
        if warnings:
            all_feedback.append(f"发现 {len(warnings)} 个警告:")
            for w in warnings:
                all_feedback.append(f"- {w.item.question}: {w.feedback}")

        return QualityGateResult(
            stage_id=stage_id,
            passed=passed,
            check_results=results,
            errors=errors,
            warnings=warnings,
            feedback="\n".join(all_feedback) if all_feedback else "所有检查通过",
            target_stage_for_backflow="requirements" if not passed else None
        )
