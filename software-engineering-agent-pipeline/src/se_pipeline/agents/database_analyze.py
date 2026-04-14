"""
DatabaseAnalyzeAgent - 数据库结构推导分析Agent
职责：
1. 从后端代码（ORM模型、SQL文件、migrations）推导数据库表结构
2. 分析数据库设计合理性
3. 输出发现的设计问题
"""
from pathlib import Path
from typing import List, Optional, Dict
import yaml
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import DatabaseAnalysisResult, CodeStructure

from ..prompts import get_prompt


class DatabaseAnalyzeAgent(BaseAgent):
    """数据库分析Agent - 从代码推导数据库结构，分析设计质量"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """执行数据库结构分析"""
        code_struct = state.code_structure
        if not code_struct:
            state.database_analysis = DatabaseAnalysisResult(
                stage_id="database_analyze",
                project_id=state.project_id,
                data=DatabaseAnalysisResult.DatabaseAnalysisData(
                    summary="No code structure information available."
                )
            )
            state.update_timestamp()
            return state

        if not code_struct.data.database_detected and not code_struct.data.backend_detected:
            # 没有检测到数据库相关代码，跳过
            state.database_analysis = DatabaseAnalysisResult(
                stage_id="database_analyze",
                project_id=state.project_id,
                data=DatabaseAnalysisResult.DatabaseAnalysisData(
                    database_type=None,
                    derived_tables=[],
                    issues=[],
                    summary="No database related code detected in this project."
                )
            )
            state.update_timestamp()
            return state

        target_dir = state.target_code_dir
        assert target_dir is not None

        # 收集数据库相关文件
        db_files = self._collect_database_files(Path(target_dir))

        # 构建上下文
        context = self._build_context(code_struct, db_files)
        # 如果有回流反馈（上次质量闸门不通过），添加到上下文
        if state.backflow_feedback:
            context += "\n\n# 上次质量检查反馈\n"
            context += "上次分析未通过质量检查，反馈意见如下，请根据反馈改进你的分析:\n"
            context += state.backflow_feedback
            context += "\n"
        prompt_template = get_prompt("database_analyze")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM分析
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析结果
        parsed = self._parse_response(response_text)

        # 构建制品
        state.database_analysis = DatabaseAnalysisResult(
            stage_id="database_analyze",
            project_id=state.project_id,
            data=DatabaseAnalysisResult.DatabaseAnalysisData(**parsed)
        )

        state.update_timestamp()
        return state

    def _detect_database_type(self, detected_tech: List[CodeStructure.DetectedTech]) -> Optional[str]:
        """识别数据库类型"""
        for tech in detected_tech:
            if tech.category == "database" or "SQL" in tech.name or "database" in tech.name.lower():
                if "postgres" in tech.name.lower() or "postgresql" in tech.name.lower():
                    return "PostgreSQL"
                if "mysql" in tech.name.lower():
                    return "MySQL"
                if "sqlite" in tech.name.lower():
                    return "SQLite"
                if "mongo" in tech.name.lower():
                    return "MongoDB"
                return tech.name
        return None

    def _collect_database_files(self, root_dir: Path) -> List[Dict[str, str]]:
        """收集数据库相关文件（ORM模型、SQL文件、migrations）"""
        db_files = []

        # 常见位置
        search_patterns = [
            "**/*schema*.sql",
            "**/*migrate*.sql",
            "**/migrations/*.py",
            "**/migrations/*.sql",
            "**/models/*.py",
            "**/models/*.java",
            "**/models/*.go",
            "**/entity/*.java",
            "**/entities/*.go",
            "**/**model*.py",
            "**/**schema*.py",
        ]

        for pattern in search_patterns:
            for fpath in root_dir.glob(pattern):
                if fpath.is_file():
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        db_files.append({
                            "path": str(fpath.relative_to(root_dir)),
                            "content": content[:4000]  # 限制大小
                        })
                    except Exception:
                        continue

        # 如果太多，只保留前几个
        return db_files[:10]

    def _build_context(self, code_struct: CodeStructure, db_files: List[Dict[str, str]]) -> str:
        """构建LLM上下文"""
        lines = []
        lines.append("# 代码结构分析结果")
        lines.append(f"目录树:\n```\n{code_struct.data.directory_tree}\n```")
        lines.append("")
        lines.append(f"架构摘要:\n{code_struct.data.summary}")
        lines.append("")
        lines.append("# 识别出的数据库信息")
        database_type = self._detect_database_type(code_struct.data.detected_tech)
        lines.append(f"Detected database type: {database_type}")
        lines.append("")
        lines.append("# 收集到的数据库相关文件内容")
        for f in db_files:
            lines.append(f"## {f['path']}")
            lines.append("```")
            lines.append(f["content"])
            lines.append("```")
            lines.append("")

        lines.append("# 任务")
        lines.append("1. 从提供的代码/ SQL文件推导出数据库表结构")
        lines.append("2. 分析数据库设计是否合理：")
        lines.append("   - 是否符合第三范式？有没有不必要的冗余？")
        "   - 主键设计是否合理？"
        "   - 外键关系是否正确？"
        "   - 索引设计是否合理？哪些字段应该加索引？"
        "   - 约束是否完整？（非空、唯一、外键）"
        lines.append("3. 列出发现的问题，每个问题包含：问题ID、位置（表名/文件）、问题类型、严重程度、问题描述")
        lines.append("")
        lines.append("请用 YAML 格式输出：")
        lines.append("```yaml")
        lines.append("database_type: \"数据库类型\"")
        lines.append("derived_tables:")
        lines.append("  - table_name: users")
        lines.append("    detected_from: app/models/user.py")
        lines.append("    columns:")
        lines.append("      - name: id")
        lines.append("        type: INTEGER")
        lines.append("        constraints: primary key")
        lines.append("    ... more tables")
        lines.append("issues:")
        lines.append("  - issue_id: db-01")
        lines.append("    location: table users")
        lines.append("    issue_type: design")
        lines.append("    severity: warning")
        lines.append("    description: 问题描述")
        lines.append("... more issues")
        lines.append("summary: |")
        lines.append("  这里是数据库设计整体分析总结")
        lines.append("```")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> dict:
        """解析LLM响应，提取YAML结果
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
                required = ["derived_tables", "issues", "summary"]
                for field in required:
                    if field not in data:
                        data[field] = [] if field in ["derived_tables", "issues"] else "No summary provided."
                if "database_type" not in data:
                    data["database_type"] = None
                return data
        except Exception:
            # YAML解析失败，尝试提取尽可能多的issues
            pass

        # 解析失败，但尝试提取尽可能多的信息
        issues = []
        derived_tables = []
        issue_id_counter = 1
        lines = response_text.splitlines()
        capture_summary = []
        in_issues = False
        in_tables = False

        for line in lines:
            if "derived_tables:" in line:
                in_tables = True
                continue
            if "issues:" in line:
                in_issues = True
                in_tables = False
                continue
            if "summary:" in line:
                in_issues = False
                in_tables = False
                continue
            if in_tables and line.strip().startswith("-"):
                # table entry
                derived_tables.append({
                    "table_name": "unknown",
                    "detected_from": "unknown",
                    "columns": [],
                })
            elif in_issues and line.strip().startswith("-") or line.strip().startswith("  -"):
                # 新issue开始
                issues.append({
                    "issue_id": f"db-{issue_id_counter:02d}",
                    "location": "unknown",
                    "issue_type": "design",
                    "severity": "warning",
                    "description": line.strip().lstrip("- "),
                })
                issue_id_counter += 1
            elif in_issues and issues and line.strip():
                issues[-1]["description"] += " " + line.strip()
            else:
                capture_summary.append(line)

        return {
            "database_type": None,
            "derived_tables": derived_tables,
            "issues": issues,
            "summary": "\n".join(capture_summary)[:1000]
        }
