"""
BackendReviewAgent - 后端代码评审Agent
职责：
1. 基于识别出的后端技术栈，分析目录结构/模块划分合理性
2. 按后端语言做针对性静态代码检查
3. 输出发现的问题列表
"""
from pathlib import Path
from typing import List, Optional, Dict
import yaml
from langchain_openai import ChatOpenAI

from .base import BaseAgent
from ..types.pipeline import PipelineState
from ..types.artifacts import BackendReviewResult, CodeStructure

from ..prompts import get_prompt


class BackendReviewAgent(BaseAgent):
    """后端代码评审Agent - 分析后端架构和代码质量"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm

    async def run(self, state: PipelineState) -> PipelineState:
        """执行后端代码评审"""
        code_struct = state.code_structure
        if not code_struct:
            # 没有代码结构信息，输出空结果
            state.backend_review = BackendReviewResult(
                stage_id="backend_review",
                project_id=state.project_id,
                data=BackendReviewResult.BackendReviewData(
                    directory_structure_review="No code structure information available.",
                    issues=[]
                )
            )
            state.update_timestamp()
            return state

        if not code_struct.data.backend_detected:
            # 没有检测到后端代码，跳过
            state.backend_review = BackendReviewResult(
                stage_id="backend_review",
                project_id=state.project_id,
                data=BackendReviewResult.BackendReviewData(
                    backend_type=None,
                    backend_framework=None,
                    directory_structure_review="No backend code detected in this project.",
                    issues=[]
                )
            )
            state.update_timestamp()
            return state

        target_dir = state.target_code_dir
        assert target_dir is not None

        # 收集关键后端文件内容
        key_files = self._collect_key_backend_files(Path(target_dir), code_struct.data.detected_tech)

        # 构建上下文
        context = self._build_context(code_struct, key_files)
        prompt_template = get_prompt("backend_review")
        full_prompt = prompt_template.replace("{{CONTEXT}}", context)

        # 调用LLM分析
        response = self.llm.invoke(full_prompt)
        response_text = response.content.strip()

        # 解析结果
        parsed = self._parse_response(response_text)

        # 构建制品
        state.backend_review = BackendReviewResult(
            stage_id="backend_review",
            project_id=state.project_id,
            data=BackendReviewResult.BackendReviewData(**parsed)
        )

        state.update_timestamp()
        return state

    def _detect_backend_type(self, detected_tech: List[CodeStructure.DetectedTech]) -> tuple[Optional[str], Optional[str]]:
        """识别后端语言和框架"""
        backend_type = None
        framework = None

        for tech in detected_tech:
            if tech.category == "backend":
                if tech.name in ["Python", "Java", "Go", "Node.js", "Rust", "PHP", "Ruby", "C++", "C#"]:
                    backend_type = tech.name
                if tech.name in ["Django", "FastAPI", "Flask", "Express", "NestJS", "Spring Boot", "Django", "FastAPI"]:
                    framework = tech.name

        # 如果没找到具体框架，根据语言推断
        if not framework:
            if backend_type == "Python":
                # 看有没有FastAPI/Django标记
                pass

        return backend_type, framework

    def _collect_key_backend_files(self, root_dir: Path, detected_tech: List[CodeStructure.DetectedTech]) -> List[Dict[str, str]]:
        """收集关键后端文件内容"""
        key_files = []

        # 优先读取配置文件
        config_files = [
            "pyproject.toml", "requirements.txt", "setup.py", "pom.xml", "build.gradle",
            "go.mod", "Cargo.toml", "package.json", "main.go", "app.py", "main.py"
        ]
        for fname in config_files:
            fpath = root_dir / fname
            if fpath.exists():
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    key_files.append({
                        "path": str(fpath.relative_to(root_dir)),
                        "content": content[:2000]
                    })
                except Exception:
                    pass

        # 查找src/app/api目录
        search_dirs = [root_dir / "src", root_dir / "app", root_dir / "api"]
        for base_dir in search_dirs:
            if base_dir.exists() and base_dir.is_dir():
                # 查找入口文件
                entry_files = ["main.py", "app.py", "__main__.py", "server.py", "index.js"]
                for fname in entry_files:
                    fpath = base_dir / fname
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

                # 查找models目录（数据库模型）
                models_dir = base_dir / "models"
                if models_dir.exists():
                    model_files = list(models_dir.glob("*.py")) + list(models_dir.glob("*.java")) + list(models_dir.glob("*.go"))
                    if model_files:
                        # 读取一个模型文件作为示例
                        try:
                            with open(model_files[0], 'r', encoding='utf-8') as f:
                                content = f.read()
                            key_files.append({
                                "path": str(model_files[0].relative_to(root_dir)),
                                "content": content[:3000]
                            })
                        except Exception:
                            pass

                # 查找routes/api目录
                routes_dir = base_dir / "routes"
                if routes_dir.exists():
                    route_files = list(routes_dir.glob("*.py")) + list(routes_dir.glob("*.js"))
                    if route_files and len(route_files) > 0:
                        try:
                            with open(route_files[0], 'r', encoding='utf-8') as f:
                                content = f.read()
                            key_files.append({
                                "path": str(route_files[0].relative_to(root_dir)),
                                "content": content[:3000]
                            })
                        except Exception:
                            pass
                break

        return key_files

    def _build_context(self, code_struct: CodeStructure, key_files: List[Dict[str, str]]) -> str:
        """构建LLM上下文"""
        lines = []
        lines.append("# 代码结构分析结果")
        lines.append(f"目录树:\n```\n{code_struct.data.directory_tree}\n```")
        lines.append("")
        lines.append(f"架构摘要:\n{code_struct.data.summary}")
        lines.append("")
        lines.append("# 识别出的后端技术")
        backend_type, backend_framework = self._detect_backend_type(code_struct.data.detected_tech)
        lines.append(f"Detected backend language: {backend_type}")
        lines.append(f"Detected backend framework: {backend_framework}")
        lines.append("")
        lines.append("# 关键文件内容")
        for f in key_files:
            lines.append(f"## {f['path']}")
            lines.append("```")
            lines.append(f["content"])
            lines.append("```")
            lines.append("")

        lines.append("# 任务")
        lines.append("请分析这个后端项目：")
        lines.append("1. 目录结构/模块划分是否合理？为什么不合理？怎么改进？")
        lines.append("2. 检查代码，发现潜在的质量问题：")
        lines.append("   - 架构分层是否清晰？")
        lines.append("   - 命名：变量/函数/类命名是否清晰可读？")
        lines.append("   - 复杂度：函数/方法是否过大过于复杂？是否需要拆分？")
        lines.append("   - 错误处理：是否有足够的错误处理和异常捕获？")
        lines.append("   - 重复代码：是否存在明显的重复代码？")
        lines.append("   - 注释：关键逻辑是否有足够的注释？")
        lines.append("   - 安全问题：是否存在明显的安全问题（注入、认证、权限等）？")
        lines.append("   - 性能问题：是否存在明显的性能问题（N+1查询、循环查询等）？")
        lines.append("")
        lines.append("请输出分析结果，每个问题需要包含：问题ID、位置（文件路径）、问题类型、严重程度（error/warning/info）、问题描述和原因")
        lines.append("")
        lines.append("请用 YAML 格式输出：")
        lines.append("```yaml")
        lines.append("backend_type: \"语言名称\"")
        lines.append("backend_framework: \"框架名称\"")
        lines.append("directory_structure_review: |")
        lines.append("  这里是对目录结构的整体评审意见")
        lines.append("issues:")
        lines.append("  - issue_id: issue-01")
        lines.append("    location: src/app.py")
        lines.append("    issue_type: architecture")
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
            pass

        # 解析失败，返回默认结构
        return {
            "backend_type": None,
            "backend_framework": None,
            "directory_structure_review": response_text[:1000],
            "issues": [],
            "summary": "Failed to parse structured output. See directory structure review above."
        }
