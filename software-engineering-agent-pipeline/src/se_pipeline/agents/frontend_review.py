"""
FrontendReviewAgent - 前端代码评审Agent
职责：
1. 基于识别出的前端技术栈，分析目录结构合理性
2. 对前端代码做针对性静态检查
3. 输出发现的问题列表
"""
from pathlib import Path
from typing import List, Optional, Dict
import yaml
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import FrontendReviewResult, CodeStructure

from ..prompts import get_prompt


class FrontendReviewAgent(BaseAgent):
    """前端代码评审Agent - 分析前端架构和代码质量"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """执行前端代码评审"""
        code_struct = state.code_structure
        if not code_struct:
            # 没有代码结构信息，输出空结果
            state.frontend_review = FrontendReviewResult(
                stage_id="frontend_review",
                project_id=state.project_id,
                data=FrontendReviewResult.FrontendReviewData(
                    directory_structure_review="No code structure information available.",
                    issues=[]
                )
            )
            state.update_timestamp()
            return state

        if not code_struct.data.frontend_detected:
            # 没有检测到前端代码，跳过
            state.frontend_review = FrontendReviewResult(
                stage_id="frontend_review",
                project_id=state.project_id,
                data=FrontendReviewResult.FrontendReviewData(
                    frontend_type=None,
                    directory_structure_review="No frontend code detected in this project.",
                    issues=[]
                )
            )
            state.update_timestamp()
            return state

        target_dir = state.target_code_dir
        assert target_dir is not None

        # 收集关键前端文件内容
        key_files = self._collect_key_frontend_files(Path(target_dir), code_struct.data.detected_tech)

        # 构建上下文
        context = self._build_context(code_struct, key_files)
        prompt_template = get_prompt("frontend_review")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM分析
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析结果
        parsed = self._parse_response(response_text)

        # 构建制品
        state.frontend_review = FrontendReviewResult(
            stage_id="frontend_review",
            project_id=state.project_id,
            data=FrontendReviewResult.FrontendReviewData(**parsed)
        )

        state.update_timestamp()
        return state

    def _detect_frontend_type(self, detected_tech: List[CodeStructure.DetectedTech]) -> Optional[str]:
        """识别前端框架类型"""
        for tech in detected_tech:
            if tech.name in ["Next.js", "React", "Vue", "Angular", "Vite"]:
                return tech.name
        # 看扩展名
        if any(t.name == "JSX" or t.name == "TSX" for t in detected_tech):
            return "React (likely)"
        if any(t.name == "VUE" for t in detected_tech):
            return "Vue (likely)"
        return "Vanilla JS"

    def _collect_key_frontend_files(self, root_dir: Path, detected_tech: List[CodeStructure.DetectedTech]) -> List[Dict[str, str]]:
        """收集关键前端文件内容"""
        key_files = []
        # 优先读取配置文件
        config_files = ["package.json", "tsconfig.json", "vite.config.ts", "vite.config.js", "next.config.js", "next.config.ts"]
        for fname in config_files:
            fpath = root_dir / fname
            if fpath.exists():
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    key_files.append({
                        "path": str(fpath.relative_to(root_dir)),
                        "content": content[:2000]  # 限制长度
                    })
                except Exception:
                    pass

        # 查找src目录下的主要入口文件
        src_dir = root_dir / "src"
        if src_dir.exists() and src_dir.is_dir():
            entry_files = ["index.html", "index.js", "index.ts", "App.tsx", "App.jsx", "main.tsx", "main.jsx"]
            for fname in entry_files:
                fpath = src_dir / fname
                if fpath.exists():
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        key_files.append({
                            "path": str(fpath.relative_to(root_dir)),
                            "content": content[:3000]
                        })
                    except Exception:
                        pass

            # 读取components目录结构（不读全部内容，太大会超token）
            components_dir = src_dir / "components"
            if components_dir.exists():
                component_files = list(components_dir.glob("*.tsx")) + list(components_dir.glob("*.jsx")) + list(components_dir.glob("*.vue"))
                if component_files:
                    # 只列文件名，读一个示例
                    # 读第一个组件作为示例
                    try:
                        with open(component_files[0], 'r', encoding='utf-8') as f:
                            content = f.read()
                        key_files.append({
                            "path": str(component_files[0].relative_to(root_dir)),
                            "content": content[:3000]
                        })
                    except Exception:
                        pass

        return key_files

    def _build_context(self, code_struct: CodeStructure, key_files: List[Dict[str, str]]) -> str:
        """构建LLM上下文"""
        lines = []
        lines.append("# 代码结构分析结果")
        lines.append(f"目录树:\n```\n{code_struct.data.directory_tree}\n```")
        lines.append("")
        lines.append(f"架构摘要:\n{code_struct.data.summary}")
        lines.append("")
        lines.append("# 识别出的前端技术")
        frontend_type = self._detect_frontend_type(code_struct.data.detected_tech)
        lines.append(f"Detected frontend type: {frontend_type}")
        lines.append("")
        lines.append("# 关键文件内容")
        for f in key_files:
            lines.append(f"## {f['path']}")
            lines.append("```")
            lines.append(f["content"])
            lines.append("```")
            lines.append("")

        lines.append("# 任务")
        lines.append("请分析这个前端项目：")
        lines.append("1. 目录结构划分是否合理？为什么不合理？怎么改进？")
        lines.append("2. 检查代码，发现潜在的质量问题（命名、复杂度、可维护性、性能、安全等）")
        lines.append("3. 请输出分析结果，每个问题需要包含：问题ID、位置（文件路径）、问题类型、严重程度（error/warning/info）、问题描述和原因")
        lines.append("")
        lines.append("请用 YAML 格式输出：")
        lines.append("```yaml")
        lines.append("frontend_type: \"框架名称\"")
        lines.append("directory_structure_review: |")
        lines.append("  这里是对目录结构的整体评审意见")
        lines.append("issues:")
        lines.append("  - issue_id: issue-01")
        lines.append("    location: src/components/xxx.tsx")
        lines.append("    issue_type: naming")
        lines.append("    severity: warning")
        lines.append("    description: 问题描述")
        lines.append("... 更多问题")
        lines.append("summary: |")
        lines.append("  这里是整体总结")
        lines.append("```")

        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> dict:
        """解析LLM响应，提取YAML结果"""
        # 提取YAML块
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
                # 确保必填字段存在
                required = ["directory_structure_review", "issues"]
                for field in required:
                    if field not in data:
                        data[field] = [] if field == "issues" else "No analysis provided."
                return data
        except Exception:
            # YAML解析失败，返回默认结构
            pass

        # 解析失败，返回原始文本作为摘要
        return {
            "frontend_type": None,
            "directory_structure_review": response_text[:1000],
            "issues": [],
            "summary": "Failed to parse structured output. See directory structure review above."
        }
