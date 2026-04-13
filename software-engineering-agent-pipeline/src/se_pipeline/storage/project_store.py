"""
项目存储 - 按项目分目录保存所有阶段制品到本地文件
"""
import yaml
from typing import Optional
from pathlib import Path

from ..types.artifacts import (
    RequirementsSpec,
    CodeStructure,
    FrontendReviewResult,
    BackendReviewResult,
    DatabaseAnalysisResult,
    ConsistencyCheckResult,
    CodeReviewReport,
)
from ..types.pipeline import PipelineState


class ProjectStore:
    """项目存储管理器"""

    def __init__(self, base_dir: str = "./projects"):
        # 始终相对于当前工作目录（项目根目录）
        self.base_dir = Path.cwd() / base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: str) -> Path:
        """获取项目目录"""
        return self.base_dir / project_id

    def save_state(self, project_id: str, state: PipelineState) -> None:
        """保存流水线状态
        project_background 只存文件名，所以直接保存即可，文件始终很小
        """
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        state_file = project_dir / "pipeline_state.yaml"
        data = state.model_dump()
        with open(state_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def load_state(self, project_id: str) -> Optional[PipelineState]:
        """加载流水线状态"""
        state_file = self.get_project_dir(project_id) / "pipeline_state.yaml"
        if not state_file.exists():
            return None

        with open(state_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        from ..types.pipeline import PipelineState
        return PipelineState(**data)

    def save_requirements(self, project_id: str, spec: RequirementsSpec) -> None:
        """保存需求规格制品"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # 保存YAML - 只保存需求规格数据，不保存完整问答历史
        # 问答历史已经单独保存在 qa-history.yaml 中
        data = spec.model_dump()
        data.pop("qa_history", None)
        yaml_file = project_dir / "01-requirements.yaml"
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        # 生成Markdown文档
        md = self._generate_requirements_markdown(spec)
        md_file = project_dir / "01-requirements-spec.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md)

        # 保存问答历史单独文件
        qa_file = project_dir / "qa-history.yaml"
        with open(qa_file, "w", encoding="utf-8") as f:
            yaml.dump(spec.qa_history.model_dump(), f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def _generate_requirements_markdown(self, spec: RequirementsSpec) -> str:
        """生成Markdown格式的需求规格文档"""
        lines = []
        lines.append(f"# 需求规格说明书 - {spec.data.title}")
        lines.append("")
        lines.append(f"**项目ID**: {spec.project_id}")
        lines.append(f"**生成时间**: {spec.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**验证状态**: {'✅ 通过' if spec.verification_passed else '❌ 未通过'}")
        lines.append("")
        lines.append("## 概述")
        lines.append("")
        lines.append(spec.data.description)
        lines.append("")

        if spec.data.user_roles:
            lines.append("## 用户角色")
            lines.append("")
            for role in spec.data.user_roles:
                lines.append(f"### {role['name']}")
                lines.append(f"{role['description']}")
                lines.append("")

        if spec.data.functional_requirements:
            lines.append("## 功能需求")
            lines.append("")
            for req in spec.data.functional_requirements:
                priority = req.get('priority', 'medium')
                icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                lines.append(f"{icon} **{req.get('id', '')} {req.get('title', '')}**")
                lines.append(f"- {req.get('description', '')}")
                lines.append("")

        if spec.data.non_functional_requirements:
            lines.append("## 非功能需求")
            lines.append("")
            for req in spec.data.non_functional_requirements:
                priority = req.get('priority', 'medium')
                icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                lines.append(f"{icon} **{req.get('id', '')} {req.get('title', '')}**")
                lines.append(f"- {req.get('description', '')}")
                lines.append("")

        if spec.data.out_of_scope and len(spec.data.out_of_scope) > 0:
            lines.append("## 不在范围内（明确不做）")
            lines.append("")
            for item in spec.data.out_of_scope:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    def list_projects(self) -> list[str]:
        """列出所有项目"""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def delete_project(self, project_id: str) -> None:
        """删除项目"""
        import shutil
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

    def save_code_structure(self, project_id: str, code_struct: CodeStructure) -> None:
        """保存代码结构分析结果"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # 生成Markdown文档
        lines = []
        lines.append("# 代码结构分析")
        lines.append("")
        lines.append(f"**项目ID**: {code_struct.project_id}")
        lines.append(f"**生成时间**: {code_struct.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**根目录**: {code_struct.data.root_directory}")
        lines.append("")
        lines.append("## 目录结构")
        lines.append("")
        lines.append("```")
        lines.append(code_struct.data.directory_tree)
        lines.append("```")
        lines.append("")
        lines.append("## 文件类型统计")
        lines.append("")
        lines.append("| 扩展名 | 文件数 | 总行数 |")
        lines.append("|--------|--------|--------|")
        for ft in code_struct.data.file_types:
            lines.append(f"| {ft.extension} | {ft.count} | {ft.total_lines} |")
        lines.append("")
        lines.append("## 检测到的技术栈")
        lines.append("")
        for tech in code_struct.data.detected_tech:
            version_str = f" v{tech.version}" if tech.version else ""
            lines.append(f"- **[{tech.category}] {tech.name}**{version_str} (from {tech.detection_source})")
        lines.append("")
        lines.append("## 检测结果汇总")
        lines.append("")
        lines.append(f"- 前端代码检测: {'✅ 是' if code_struct.data.frontend_detected else '❌ 否'}")
        lines.append(f"- 后端代码检测: {'✅ 是' if code_struct.data.backend_detected else '❌ 否'}")
        lines.append(f"- 数据库相关代码检测: {'✅ 是' if code_struct.data.database_detected else '❌ 否'}")
        lines.append("")
        lines.append("## 架构摘要")
        lines.append("")
        lines.append(code_struct.data.summary)
        lines.append("")

        md_file = project_dir / "02-code-structure.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_frontend_review(self, project_id: str, review: FrontendReviewResult) -> None:
        """保存前端代码评审结果"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# 前端代码评审")
        lines.append("")
        lines.append(f"**项目ID**: {review.project_id}")
        lines.append(f"**生成时间**: {review.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if review.data.frontend_type:
            lines.append(f"**前端类型**: {review.data.frontend_type}")
        lines.append("")
        lines.append("## 目录结构评审")
        lines.append("")
        lines.append(review.data.directory_structure_review)
        lines.append("")

        if review.data.issues and len(review.data.issues) > 0:
            lines.append("## 发现的问题")
            lines.append("")
            for issue in review.data.issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(issue.severity, "🔵")
                lines.append(f"{severity_icon} **{issue.issue_id} - {issue.location}**")
                lines.append(f"- **类型**: {issue.issue_type}")
                lines.append(f"- {issue.description}")
                lines.append("")

        lines.append("## 总结")
        if review.data.summary:
            lines.append(review.data.summary)
            lines.append("")

        md_file = project_dir / "03-frontend-review.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_backend_review(self, project_id: str, review: BackendReviewResult) -> None:
        """保存后端代码评审结果"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# 后端代码评审")
        lines.append("")
        lines.append(f"**项目ID**: {review.project_id}")
        lines.append(f"**生成时间**: {review.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if review.data.backend_type:
            lines.append(f"**后端语言**: {review.data.backend_type}")
        if review.data.backend_framework:
            lines.append(f"**框架**: {review.data.backend_framework}")
        lines.append("")
        lines.append("## 目录结构评审")
        lines.append("")
        lines.append(review.data.directory_structure_review)
        lines.append("")

        if review.data.issues and len(review.data.issues) > 0:
            lines.append("## 发现的问题")
            lines.append("")
            for issue in review.data.issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(issue.severity, "🔵")
                lines.append(f"{severity_icon} **{issue.issue_id} - {issue.location}**")
                lines.append(f"- **类型**: {issue.issue_type}")
                lines.append(f"- {issue.description}")
                lines.append("")

        lines.append("## 总结")
        if review.data.summary:
            lines.append(review.data.summary)
            lines.append("")

        md_file = project_dir / "04-backend-review.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_database_analysis(self, project_id: str, analysis: DatabaseAnalysisResult) -> None:
        """保存数据库分析结果"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# 数据库结构分析")
        lines.append("")
        lines.append(f"**项目ID**: {analysis.project_id}")
        lines.append(f"**生成时间**: {analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if analysis.data.database_type:
            lines.append(f"**数据库类型**: {analysis.data.database_type}")
        lines.append("")

        if analysis.data.derived_tables and len(analysis.data.derived_tables) > 0:
            lines.append("## 推导表结构")
            lines.append("")
            for table in analysis.data.derived_tables:
                lines.append(f"### {table.table_name}")
                lines.append("")
                if table.columns:
                    lines.append("| 列名 | 类型 | 约束 | 说明 |")
                    lines.append("|------|------|------|------|")
                    for col in table.columns:
                        constraints = ", ".join(col.get("constraints", [])) if isinstance(col, dict) else ", ".join(col.constraints if hasattr(col, 'constraints') else [])
                        lines.append(f"| {col.name if hasattr(col, 'name') else col.get('name', '')} | {col.type if hasattr(col, 'type') else col.get('type', '')} | {constraints} | {col.description if hasattr(col, 'description') else col.get('description', '')} |")
                    lines.append("")
            lines.append("")

        if analysis.data.issues and len(analysis.data.issues) > 0:
            lines.append("## 发现的问题")
            lines.append("")
            for issue in analysis.data.issues:
                severity_icon = {
                    "error": "🔴",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(issue.severity, "🔵")
                lines.append(f"{severity_icon} **{issue.issue_id} - {issue.location}**")
                lines.append(f"- **类型**: {issue.issue_type}")
                lines.append(f"- {issue.description}")
                lines.append("")

        lines.append("## 总结")
        if analysis.data.summary:
            lines.append(analysis.data.summary)
            lines.append("")

        md_file = project_dir / "05-database-analysis.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_consistency_check(self, project_id: str, check: ConsistencyCheckResult) -> None:
        """保存一致性检查结果（设计文档 vs 代码实现）"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# 设计文档与代码一致性检查")
        lines.append("")
        lines.append(f"**项目ID**: {check.project_id}")
        lines.append(f"**生成时间**: {check.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if check.data.inconsistencies and len(check.data.inconsistencies) > 0:
            lines.append("## 发现的不一致")
            lines.append("")
            for item in check.data.inconsistencies:
                severity_icon = {
                    "error": "🔴",
                    "warning": "🟡",
                }.get(item.severity, "🟡")
                lines.append(f"{severity_icon} **{item.check_id} - {item.location}**: {item.description}")
                lines.append("")

        lines.append("## 总结")
        if check.data.summary:
            lines.append(check.data.summary)
            lines.append("")

        md_file = project_dir / "06-consistency-check.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def save_codereview_report(self, project_id: str, report: CodeReviewReport) -> None:
        """保存最终代码评审报告"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# 最终代码评审报告")
        lines.append("")
        lines.append(f"**项目ID**: {report.project_id}")
        lines.append(f"**生成时间**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**目标代码目录**: {report.data.target_directory}")
        lines.append("")

        lines.append("## 统计摘要")
        lines.append("")
        from collections import defaultdict
        issues_by_category = defaultdict(list)
        total_issues = 0
        error_count = 0
        warning_count = 0
        info_count = 0

        # 按category分组统计所有问题
        for issue in report.data.issues:
            total_issues += 1
            category = getattr(issue, 'category', 'other')
            issues_by_category[category].append(issue)
            severity = issue.severity
            if severity == "error":
                error_count += 1
            elif severity == "warning":
                warning_count += 1
            else:
                info_count += 1

        lines.append(f"- 总计发现问题: **{total_issues}**")
        if error_count > 0:
            lines.append(f"- 🔴 错误: {error_count}")
        if warning_count > 0:
            lines.append(f"- 🟡 警告: {warning_count}")
        if info_count > 0:
            lines.append(f"- 🔵 信息: {info_count}")
        lines.append("")

        if report.data.overall_summary:
            lines.append("## 整体评价")
            lines.append("")
            lines.append(report.data.overall_summary)
            lines.append("")

        if total_issues > 0:
            lines.append("## 详细问题列表")
            lines.append("")

            category_names = {
                "frontend": "前端问题",
                "backend": "后端问题",
                "database": "数据库问题",
                "consistency": "一致性问题",
                "other": "其他问题",
            }

            for category, issues in issues_by_category.items():
                if len(issues) == 0:
                    continue
                display_name = category_names.get(category, category)
                lines.append(f"### {display_name} ({len(issues)})")
                lines.append("")
                for issue in issues:
                    severity_icon = {
                        "error": "🔴",
                        "warning": "🟡",
                        "info": "🔵"
                    }.get(issue.severity, "🔵")
                    location = getattr(issue, 'location', 'N/A')
                    issue_type = getattr(issue, 'issue_type', 'N/A')
                    issue_id = getattr(issue, 'issue_id', '')
                    if issue_id:
                        title = f"{severity_icon} **{issue_id} - {location}**"
                    else:
                        title = f"{severity_icon} **{location}**"
                    lines.append(title)
                    lines.append(f"- **类型**: {issue_type}")
                    lines.append(f"- {issue.description}")
                    lines.append("")

        md_file = project_dir / "07-code-review-report.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
