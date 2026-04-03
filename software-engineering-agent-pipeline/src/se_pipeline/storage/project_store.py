"""
项目存储 - 按项目分目录保存所有阶段制品到本地文件
"""
import yaml
from typing import Optional
from pathlib import Path

from ..types.artifacts import RequirementsSpec
from ..types.pipeline import PipelineState


class ProjectStore:
    """项目存储管理器"""

    def __init__(self, base_dir: str = "./projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: str) -> Path:
        """获取项目目录"""
        return self.base_dir / project_id

    def save_state(self, project_id: str, state: PipelineState) -> None:
        """保存流水线状态"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        state_file = project_dir / "pipeline_state.yaml"
        with open(state_file, "w", encoding="utf-8") as f:
            yaml.dump(state.model_dump(), f, default_flow_style=False, sort_keys=False, allow_unicode=True)

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

        # 保存YAML
        yaml_file = project_dir / "01-requirements.yaml"
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(spec.model_dump(), f, default_flow_style=False, sort_keys=False, allow_unicode=True)

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

        if spec.qa_history.items:
            lines.append("## 问答澄清历史")
            lines.append("")
            for i, item in enumerate(spec.qa_history.items, 1):
                lines.append(f"### 问题 {i}")
                lines.append(f"**问题**: {item.question}")
                if item.answer:
                    lines.append(f"**回答**: {item.answer}")
                else:
                    lines.append("**状态**: ⏸ 尚未回答")
                lines.append("")

        return "\n".join(lines)

    def list_projects(self) -> list[str]:
        """列出所有项目"""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
