"""
ConsistencyCheckAgent - 设计一致性检查Agent
职责：
如果用户上传了设计文档，对比代码实现和设计文档是否一致
找出遗漏实现和不一致的地方，输出问题列表
"""
import yaml
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import ConsistencyCheckResult

from ..prompts import get_prompt


class ConsistencyCheckAgent(BaseAgent):
    """一致性检查Agent - 对比代码实现和设计文档是否一致"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """执行一致性检查"""

        # 检查是否有设计文档
        design_content = state.project_background
        if not design_content and state.attached_documents:
            # 如果project_background为空，但有上传文档，说明文档还没预处理
            # 这里直接空结果，预处理会在前面完成
            pass

        if not design_content.strip():
            # 没有设计文档，跳过检查
            state.consistency_check = ConsistencyCheckResult(
                stage_id="consistency_check",
                project_id=state.project_id,
                data=ConsistencyCheckResult.ConsistencyCheckData(
                    design_document_available=False,
                    summary="No design document provided, consistency check skipped."
                )
            )
            state.update_timestamp()
            return state

        # 收集前面所有分析结果
        context = self._build_context(state)
        # 如果有回流反馈（上次质量闸门不通过），添加到上下文
        if state.backflow_feedback:
            context += "\n\n# 上次质量检查反馈\n"
            context += "上次检查未通过质量检查，反馈意见如下，请根据反馈改进你的检查:\n"
            context += state.backflow_feedback
            context += "\n"
        prompt_template = get_prompt("consistency_check")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM对比检查
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        parsed = self._parse_response(response_text)

        # 统计不一致数量
        inconsistency_count = len(parsed.get("inconsistencies", []))
        overall_consistent = inconsistency_count == 0

        state.consistency_check = ConsistencyCheckResult(
            stage_id="consistency_check",
            project_id=state.project_id,
            data=ConsistencyCheckResult.ConsistencyCheckData(
                design_document_available=True,
                total_checks=inconsistency_count,
                inconsistencies=parsed.get("inconsistencies", []),
                summary=parsed.get("summary", "Check completed."),
                overall_consistent=overall_consistent
            )
        )

        state.update_timestamp()
        return state

    def _build_context(self, state: PipelineState) -> str:
        """构建上下文"""
        lines = []

        lines.append("# 设计文档（用户上传的设计要求）")
        lines.append("")
        lines.append(state.project_background)
        lines.append("")

        lines.append("# 代码分析结果")
        lines.append("")

        if state.code_structure:
            lines.append("## 整体架构分析")
            lines.append(state.code_structure.data.summary)
            lines.append("")

        if state.frontend_review:
            lines.append("## 前端分析 - 发现的问题")
            for issue in state.frontend_review.data.issues:
                lines.append(f"- {issue['severity']}: {issue['location']} - {issue['description']}")
            lines.append("")

        if state.backend_review:
            lines.append("## 后端分析 - 发现的问题")
            for issue in state.backend_review.data.issues:
                lines.append(f"- {issue['severity']}: {issue['location']} - {issue['description']}")
            lines.append("")

        if state.database_analysis:
            lines.append("## 数据库分析 - 推导的表结构")
            for table in state.database_analysis.data.derived_tables:
                lines.append(f"- {table['table_name']} (from {table['detected_from']})")
            lines.append("## 数据库分析 - 发现的问题")
            for issue in state.database_analysis.data.issues:
                lines.append(f"- {issue['severity']}: {issue['location']} - {issue['description']}")
            lines.append("")

        lines.append("# 任务")
        lines.append("对比设计文档和代码分析结果，检查一致性：")
        lines.append("1. 需求/功能：代码实现是否覆盖了设计文档要求的所有功能？")
        lines.append("2. 架构：代码实际架构是否符合设计文档的架构设计？")
        lines.append("3. 数据库：实际数据库结构是否符合设计文档的数据库设计？")
        lines.append("4. API：API接口设计是否符合设计文档的API契约？")
        lines.append("")
        lines.append("列出所有不一致和遗漏的地方：")
        lines.append("- 哪些功能设计了但代码没实现？")
        lines.append("- 哪些实现和设计不一致？")
        lines.append("- 设计文档有要求但代码里没找到？")
        lines.append("")
        lines.append("请用 YAML 格式输出：")
        lines.append("```yaml")
        lines.append("inconsistencies:")
        lines.append("  - check_id: c-01")
        lines.append("    location: 功能名称/模块名称")
        lines.append("    description: 描述不一致具体是什么")
        lines.append("    severity: error/warning")
        lines.append("summary: |")
        lines.append("  这里是一致性检查总结")
        lines.append("```")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> dict:
        """解析LLM响应
        如果解析失败，尝试从部分输出恢复尽可能多的数据
        """
        try:
            if "```yaml" in response_text:
                start = response_text.find("```yaml") + 7
                end = response_text.find("```", start)
                if end == -1:  # YAML被截断，没有结束标记
                    yaml_text = response_text[start:].strip()
                else:
                    yaml_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end == -1:
                    yaml_text = response_text[start:].strip()
                else:
                    yaml_text = response_text[start:end].strip()
            else:
                yaml_text = response_text.strip()

            data = yaml.safe_load(yaml_text)
            if isinstance(data, dict):
                if "inconsistencies" not in data:
                    data["inconsistencies"] = []
                if "summary" not in data:
                    data["summary"] = "Check completed."
                return data
        except Exception:
            # YAML解析失败，尝试逐行提取
            pass

        # 解析失败，尝试提取尽可能多的不一致项
        inconsistencies = []
        check_id_counter = 1
        lines = response_text.splitlines()
        capture_summary = []
        in_inconsistencies = False

        for line in lines:
            if "inconsistencies:" in line:
                in_inconsistencies = True
                continue
            if "summary:" in line:
                in_inconsistencies = False
                continue
            if in_inconsistencies and (line.strip().startswith("-") or line.strip().startswith("  -")):
                # 新不一致项开始
                inconsistencies.append({
                    "check_id": f"c-{check_id_counter:02d}",
                    "location": "unknown",
                    "description": line.strip().lstrip("- "),
                    "severity": "warning",
                })
                check_id_counter += 1
            elif in_inconsistencies and inconsistencies and line.strip():
                inconsistencies[-1]["description"] += " " + line.strip()
            else:
                capture_summary.append(line)

        return {
            "inconsistencies": inconsistencies,
            "summary": "\n".join(capture_summary)[:1000]
        }
