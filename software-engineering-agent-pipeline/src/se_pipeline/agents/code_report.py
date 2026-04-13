"""
CodeReportAgent - 汇总生成最终代码评审报告
职责：
汇总前面所有Agent发现的问题，按分类整理，生成最终评审报告
"""
from collections import defaultdict
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import CodeReviewReport, CodeReviewIssue

from ..prompts import get_prompt


class CodeReportAgent(BaseAgent):
    """最终代码评审报告生成Agent - 汇总所有问题生成完整报告"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """汇总生成最终评审报告"""
        # 收集所有问题
        all_issues = self._collect_all_issues(state)

        # 统计
        error_count = sum(1 for i in all_issues if i["severity"] == "error")
        warning_count = sum(1 for i in all_issues if i["severity"] == "warning")
        info_count = sum(1 for i in all_issues if i["severity"] == "info")

        # 构建上下文
        context = self._build_context(state, all_issues, error_count, warning_count, info_count)
        prompt_template = get_prompt("code_report")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM生成整体总结
        response = self.llm.invoke(full_prompt)
        overall_summary = response.content.strip()

        # 构建最终制品
        issues = [
            CodeReviewIssue(**issue)
            for issue in all_issues
        ]

        assert state.target_code_dir is not None

        # 收集技术栈摘要
        tech_summary = ""
        if state.code_structure:
            tech_summary = state.code_structure.data.summary

        state.codereview_report = CodeReviewReport(
            stage_id="codereview",
            project_id=state.project_id,
            data=CodeReviewReport.CodeReviewData(
                target_directory=state.target_code_dir,
                detected_tech_summary=tech_summary,
                issues=issues,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
                overall_summary=overall_summary
            )
        )

        state.update_timestamp()
        return state

    def _collect_all_issues(self, state: PipelineState) -> list[dict]:
        """收集所有Agent发现的问题"""
        all_issues = []
        issue_id_counter = 1

        # 前端问题
        if state.frontend_review and state.frontend_review.data.issues:
            for issue in state.frontend_review.data.issues:
                issue["issue_id"] = f"fr-{issue_id_counter:02d}"
                issue["category"] = "frontend"
                all_issues.append(issue)
                issue_id_counter += 1

        # 后端问题
        if state.backend_review and state.backend_review.data.issues:
            for issue in state.backend_review.data.issues:
                issue["issue_id"] = f"br-{issue_id_counter:02d}"
                issue["category"] = "backend"
                all_issues.append(issue)
                issue_id_counter += 1

        # 数据库问题
        if state.database_analysis and state.database_analysis.data.issues:
            for issue in state.database_analysis.data.issues:
                issue["issue_id"] = f"db-{issue_id_counter:02d}"
                issue["category"] = "database"
                all_issues.append(issue)
                issue_id_counter += 1

        # 一致性问题
        if state.consistency_check and state.consistency_check.data.inconsistencies:
            for issue in state.consistency_check.data.inconsistencies:
                issue["issue_id"] = f"cc-{issue_id_counter:02d}"
                issue["category"] = "consistency"
                issue["issue_type"] = "consistency"
                all_issues.append(issue)
                issue_id_counter += 1

        # 结构问题（如果架构分析发现问题，可以在这里加）
        if state.code_structure:
            # 这里结构分析的问题已经包含在summary里了，最终总结会提到
            pass

        return all_issues

    def _build_context(
        self, state: PipelineState, all_issues: list[dict],
        error_count: int, warning_count: int, info_count: int
    ) -> str:
        """构建上下文"""
        lines = []

        lines.append("# 代码评审汇总")
        lines.append(f"目标目录: {state.target_code_dir}")
        lines.append("")

        if state.code_structure:
            lines.append("## 整体架构摘要")
            lines.append(state.code_structure.data.summary)
            lines.append("")

        lines.append("## 所有发现的问题")
        lines.append(f"总计: {error_count} errors, {warning_count} warnings, {info_count} info")
        lines.append("")

        # 按分类列出
        categories = defaultdict(list)
        for issue in all_issues:
            categories[issue["category"]].append(issue)

        for category, issues in categories.items():
            category_name = {
                "structure": "架构",
                "frontend": "前端",
                "backend": "后端",
                "database": "数据库",
                "consistency": "一致性",
            }.get(category, category)
            lines.append(f"### {category_name} ({len(issues)} 个问题)")
            for issue in issues:
                loc = issue.get("location", "unknown")
                desc = issue.get("description", "no description")
                sev = issue.get("severity", "warning")
                lines.append(f"- **[{sev.upper()}]** {loc}: {desc}")
            lines.append("")

        lines.append("## 任务")
        lines.append("请生成一份整体总结：")
        lines.append("1. 这个代码库的整体质量如何？")
        lines.append("2. 最严重的问题是哪些？")
        lines.append("3. 改进优先级建议，先改什么后改什么？")
        lines.append("")
        lines.append("总结要简洁明了，突出重点。")

        return "\n".join(lines)
