"""架构生成引擎 - 控制整个架构设计流程"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from core.ai_backend import AIBackend
from core.architecture_validator import validate_architecture
from core.claude_cli import ClaudeCLIBackend
from core.openai_api import OpenAIBackend
from core.prd_loader import PRD
from utils.file_utils import ensure_dir, write_json, write_text
from utils.logger import get_logger

logger = get_logger()


class ArchitectureGenerator:
    """架构生成引擎"""

    def __init__(
        self,
        config: Config,
        prd: PRD,
        output_dir: str,
        prd_filename_prefix: str,
        max_retries: Optional[int] = None,
        dry_run: bool = False
    ):
        self.config = config
        self.prd = prd
        self.output_dir = output_dir
        self.prd_filename_prefix = prd_filename_prefix
        self.max_retries = max_retries if max_retries is not None else config.max_retries
        self.dry_run = dry_run
        self.ai_backend: Optional[AIBackend] = None
        self._architecture_prompt: Optional[str] = None
        self._validation_prompt: Optional[str] = None

    def _init_ai_backend(self) -> bool:
        """初始化AI后端"""
        if self.config.ai_backend == "claude":
            self.ai_backend = ClaudeCLIBackend(
                claude_cmd=self.config.claude_cmd,
                working_dir=self.output_dir
            )
        elif self.config.ai_backend == "openai":
            self.ai_backend = OpenAIBackend(
                api_key=self.config.openai_api_key,
                model=self.config.openai_model,
                base_url=self.config.openai_base_url,
                max_tokens=self.config.openai_max_tokens,
                working_dir=self.output_dir
            )
        else:
            logger.error(f"未知AI后端: {self.config.ai_backend}")
            return False

        if not self.ai_backend.is_available():
            logger.error(f"AI后端 {self.config.ai_backend} 不可用")
            return False

        logger.info(f"AI后端初始化完成: {self.config.ai_backend}")
        return True

    def _load_prompts(self) -> bool:
        """加载提示词模板"""
        try:
            with open("prompts/architecture-design.md", "r", encoding="utf-8") as f:
                self._architecture_prompt = f.read()
            with open("prompts/validation-review.md", "r", encoding="utf-8") as f:
                self._validation_prompt = f.read()
            return True
        except Exception as e:
            logger.error(f"加载提示词模板失败: {e}")
            return False

    def _build_architecture_prompt(self) -> str:
        """构建架构设计prompt"""
        # 转换PRD为JSON字符串
        prd_json = json.dumps({
            "project": self.prd.project,
            "branch_name": self.prd.branch_name,
            "description": self.prd.description,
            "user_stories": [
                {
                    "id": us.id,
                    "title": us.title,
                    "description": us.description,
                    "acceptance_criteria": us.acceptance_criteria,
                    "priority": us.priority
                }
                for us in self.prd.user_stories
            ]
        }, ensure_ascii=False, indent=2)

        return self._architecture_prompt.replace("{{PRD_JSON}}", prd_json)

    def _build_validation_prompt(
        self,
        architecture_json: Dict[str, Any],
        errors: Optional[List[str]] = None
    ) -> str:
        """构建验证评审prompt"""
        arch_json_str = json.dumps(architecture_json, ensure_ascii=False, indent=2)
        prompt = self._validation_prompt.replace("{{ARCHITECTURE_JSON}}", arch_json_str)
        prompt = prompt.replace("{{PRD_DESCRIPTION}}", self.prd.description)

        if errors:
            error_text = "\n".join(f"- {err}" for err in errors)
            prompt = prompt.replace("{{ERRORS}}", error_text)
        else:
            prompt = prompt.replace("{{ERRORS}}", "没有之前的错误")

        return prompt

    def generate(self) -> Tuple[Optional[Dict[str, Any]], str]:
        """生成架构设计

        Returns:
            (architecture_dict, error_message)
        """
        # 初始化
        if not self._init_ai_backend():
            return None, "AI后端初始化失败"
        if not self._load_prompts():
            return None, "加载提示词模板失败"

        ensure_dir(self.output_dir)

        # 生成尝试循环
        for attempt in range(self.max_retries + 1):
            logger.info(f"第 {attempt + 1}/{self.max_retries + 1} 次生成尝试")

            if self.dry_run:
                logger.info("干跑模式，跳过AI调用")
                return None, "干跑模式"

            # 第一轮：生成架构
            prompt = self._build_architecture_prompt()
            content = self.ai_backend.generate(prompt)
            if content is None:
                logger.error("AI生成失败，重试...")
                continue

            # 验证JSON
            architecture = validate_architecture(content, self.output_dir, attempt + 1)
            if architecture is None:
                logger.error("JSON验证失败，重试...")
                continue

            # 添加metadata（初始版本）
            if "metadata" not in architecture:
                architecture["metadata"] = {}
            architecture["metadata"]["generatedAt"] = datetime.utcnow().isoformat() + "Z"
            architecture["metadata"]["sourcePrd"] = self.prd.project
            architecture["metadata"]["version"] = f"attempt{attempt + 1} (initial)"

            # 第一轮生成完成后立刻保存MD预览，验证前就能看
            attempt_md_path = f"{self.output_dir}/{self.prd_filename_prefix}.architecture_attempt{attempt + 1}.md"
            attempt_md_content = self._architecture_to_markdown(architecture)
            if write_text(attempt_md_path, attempt_md_content):
                logger.info(f"尝试 {attempt + 1} 初始架构预览已保存: {attempt_md_path}")
            else:
                logger.warning(f"保存尝试 {attempt + 1} 预览失败")

            # 第二轮：AI自评验证
            if self.config.max_validation_attempts > 0:
                logger.info("开始第二轮AI自评验证...")
                validation_prompt = self._build_validation_prompt(architecture)
                validation_content = self.ai_backend.generate(validation_prompt)
                if validation_content is None:
                    logger.warning("AI验证失败，使用原结果")
                else:
                    validated_arch = validate_architecture(validation_content, self.output_dir, attempt + 1)
                    if validated_arch is not None:
                        architecture = validated_arch
                        # 更新metadata
                        if "metadata" not in architecture:
                            architecture["metadata"] = {}
                        architecture["metadata"]["generatedAt"] = datetime.utcnow().isoformat() + "Z"
                        architecture["metadata"]["sourcePrd"] = self.prd.project
                        architecture["metadata"]["version"] = f"attempt{attempt + 1} (validated)"
                        # 覆盖保存改进后的MD
                        attempt_md_content = self._architecture_to_markdown(architecture)
                        if write_text(attempt_md_path, attempt_md_content):
                            logger.info(f"AI自评验证通过，已更新架构预览: {attempt_md_path}")
                        else:
                            logger.warning(f"更新尝试 {attempt + 1} 预览失败")
                        logger.info("AI自评验证通过，使用改进后的架构")
                    else:
                        logger.warning("验证后的JSON无效，使用原结果")

            logger.info("架构生成成功")
            return architecture, ""

        return None, f"经过 {self.max_retries + 1} 次尝试仍然失败"

    def _architecture_to_markdown(self, architecture: Dict[str, Any]) -> str:
        """将架构转换为可读的Markdown格式"""
        lines = []

        # 标题
        project = architecture.get("project", {})
        lines.append(f"# {project.get('name', '项目')}\n\n")

        # 项目描述
        description = project.get("description")
        if description:
            lines.append(f"{description}\n\n")

        # 架构概览
        arch = architecture.get("architecture", {})
        if arch:
            overview = arch.get("overview")
            if overview:
                lines.append("## 架构概览\n\n")
                lines.append(f"{overview}\n\n")

            architecture_pattern = arch.get("architecturePattern")
            if architecture_pattern:
                lines.append(f"**架构模式**: {architecture_pattern}\n\n")

            # 技术栈
            tech_stack = arch.get("techStack")
            if tech_stack:
                lines.append("## 技术栈\n\n")

                backend = tech_stack.get("backend")
                if backend:
                    lines.append("### 后端\n\n")
                    if backend.get("language"):
                        lines.append(f"- **语言**: {backend['language']}\n")
                    if backend.get("framework"):
                        lines.append(f"- **框架**: {', '.join(backend['framework'])}\n")
                    if backend.get("database"):
                        lines.append(f"- **数据库**: {backend['database']}\n")
                    if backend.get("orm"):
                        lines.append(f"- **ORM**: {backend['orm']}\n")
                    if backend.get("authentication"):
                        lines.append(f"- **认证**: {backend['authentication']}\n")
                    lines.append("\n")

                frontend = tech_stack.get("frontend")
                if frontend:
                    lines.append("### 前端\n\n")
                    if frontend.get("language"):
                        lines.append(f"- **语言**: {frontend['language']}\n")
                    if frontend.get("framework"):
                        lines.append(f"- **框架**: {', '.join(frontend['framework'])}\n")
                    if frontend.get("buildTool"):
                        lines.append(f"- **构建工具**: {frontend['buildTool']}\n")
                    if frontend.get("cssFramework"):
                        lines.append(f"- **CSS框架**: {frontend['cssFramework']}\n")
                    lines.append("\n")

                deployment = tech_stack.get("deployment")
                if deployment:
                    lines.append("### 部署\n\n")
                    for item in deployment:
                        lines.append(f"- {item}\n")
                    lines.append("\n")

        # 后端模块
        backend = architecture.get("backend")
        if backend and backend.get("modules"):
            lines.append("## 后端模块\n\n")
            for module in backend["modules"]:
                lines.append(f"### {module.get('name', '模块')}\n\n")
                description = module.get("description")
                if description:
                    lines.append(f"{description}\n\n")
                lines.append(f"- **ID**: `{module.get('id', '')}`\n")
                directory = module.get("directory")
                if directory:
                    lines.append(f"- **目录**: `{directory}`\n")
                if module.get("files"):
                    lines.append("- **文件**:\n")
                    for f in module["files"]:
                        desc = f" - {f.get('description', '')}" if f.get('description') else ""
                        lines.append(f"  - `{f.get('path', '')}`{desc}\n")
                lines.append("\n")

        # 数据模型
        if backend and backend.get("dataModels"):
            lines.append("## 数据模型\n\n")
            for model in backend["dataModels"]:
                lines.append(f"### {model.get('name', '模型')}\n\n")
                description = model.get("description")
                if description:
                    lines.append(f"{description}\n\n")
                table_name = model.get("tableName")
                if table_name:
                    lines.append(f"**表名**: `{table_name}`\n\n")
                if model.get("fields"):
                    lines.append("| 字段名 | 类型 | 约束 | 默认值 | 说明 |\n")
                    lines.append("|--------|------|------|--------|------|\n")
                    for field in model["fields"]:
                        name = field.get("name", "")
                        type_ = field.get("type", "")
                        constraints = ", ".join(field.get("constraints", [])) if field.get("constraints") else ""
                        default = field.get("default", "")
                        desc = field.get("description", "")
                        lines.append(f"| {name} | {type_} | {constraints} | {default} | {desc} |\n")
                    lines.append("\n")
                if model.get("relationships"):
                    lines.append("**关系**:\n\n")
                    for rel in model["relationships"]:
                        lines.append(f"- {rel.get('type', '')} → {rel.get('targetModel', '')}, 外键: `{rel.get('foreignKey', '')}`\n")
                    lines.append("\n")

        # API 端点
        if backend and backend.get("apiEndpoints"):
            lines.append("## API 端点\n\n")
            lines.append("| 方法 | 路径 | 认证 | 说明 |\n")
            lines.append("|------|------|------|------|\n")
            for endpoint in backend["apiEndpoints"]:
                method = endpoint.get("method", "")
                path = endpoint.get("path", "")
                auth = "✓ 需要" if endpoint.get("authentication") else "✗ 不需要"
                description = endpoint.get("description", "")
                lines.append(f"| {method} | `{path}` | {auth} | {description} |\n")
            lines.append("\n")

        # 后端依赖
        if backend and backend.get("dependencies"):
            lines.append("## 后端依赖\n\n")
            lines.append("| 包名 | 版本 | 说明 |\n")
            lines.append("|------|------|------|\n")
            for dep in backend["dependencies"]:
                name = dep.get("name", "")
                version = dep.get("version", "") or ""
                description = dep.get("description", "") or ""
                lines.append(f"| {name} | {version} | {description} |\n")
            lines.append("\n")

        # 前端模块
        frontend = architecture.get("frontend")
        if frontend and frontend.get("modules"):
            lines.append("## 前端模块\n\n")
            for module in frontend["modules"]:
                lines.append(f"### {module.get('name', '模块')}\n\n")
                description = module.get("description")
                if description:
                    lines.append(f"{description}\n\n")
                lines.append(f"- **ID**: `{module.get('id', '')}`\n")
                directory = module.get("directory")
                if directory:
                    lines.append(f"- **目录**: `{directory}`\n")
                if module.get("files"):
                    lines.append("- **文件**:\n")
                    for f in module["files"]:
                        desc = f" - {f.get('description', '')}" if f.get('description') else ""
                        lines.append(f"  - `{f.get('path', '')}`{desc}\n")
                lines.append("\n")

        # 前端路由
        if frontend and frontend.get("routes"):
            lines.append("## 前端路由\n\n")
            lines.append("| 路径 | 组件 | 说明 |\n")
            lines.append("|------|----------|------|\n")
            for route in frontend["routes"]:
                path = route.get("path", "")
                component = route.get("component", "")
                description = route.get("description", "")
                lines.append(f"| `{path}` | {component} | {description} |\n")
            lines.append("\n")

        # 前端依赖
        if frontend and frontend.get("dependencies"):
            lines.append("## 前端依赖\n\n")
            lines.append("| 包名 | 版本 | 说明 |\n")
            lines.append("|------|------|------|\n")
            for dep in frontend["dependencies"]:
                name = dep.get("name", "")
                version = dep.get("version", "") or ""
                description = dep.get("description", "") or ""
                lines.append(f"| {name} | {version} | {description} |\n")
            lines.append("\n")

        # 共享依赖
        shared = architecture.get("shared")
        if shared and shared.get("dependencies"):
            lines.append("## 共享依赖\n\n")
            for section, deps in shared["dependencies"].items():
                lines.append(f"### {section.title()}\n\n")
                lines.append("| 包名 | 版本 | 说明 |\n")
                lines.append("|------|------|------|\n")
                for dep in deps:
                    name = dep.get("name", "")
                    version = dep.get("version", "") or ""
                    description = dep.get("description", "") or ""
                    lines.append(f"| {name} | {version} | {description} |\n")
                lines.append("\n")

        # 开发配置
        if backend and backend.get("development"):
            lines.append("## 开发配置 - 后端\n\n")
            dev = backend["development"]
            if dev.get("setupSteps"):
                lines.append("**安装步骤**:\n\n")
                for i, step in enumerate(dev["setupSteps"], 1):
                    lines.append(f"{i}. {step}\n")
                lines.append("\n")
            if dev.get("buildCommand"):
                lines.append(f"**构建命令**: `{dev['buildCommand']}`\n\n")
            if dev.get("devCommand"):
                lines.append(f"**开发命令**: `{dev['devCommand']}`\n\n")
            if dev.get("testCommand"):
                lines.append(f"**测试命令**: `{dev['testCommand']}`\n\n")
            if dev.get("lintCommand"):
                lines.append(f"**Lint命令**: `{dev['lintCommand']}`\n\n")

        if frontend and frontend.get("development"):
            lines.append("## 开发配置 - 前端\n\n")
            dev = frontend["development"]
            if dev.get("setupSteps"):
                lines.append("**安装步骤**:\n\n")
                for i, step in enumerate(dev["setupSteps"], 1):
                    lines.append(f"{i}. {step}\n")
                lines.append("\n")
            if dev.get("buildCommand"):
                lines.append(f"**构建命令**: `{dev['buildCommand']}`\n\n")
            if dev.get("devCommand"):
                lines.append(f"**开发命令**: `{dev['devCommand']}`\n\n")
            if dev.get("testCommand"):
                lines.append(f"**测试命令**: `{dev['testCommand']}`\n\n")
            if dev.get("lintCommand"):
                lines.append(f"**Lint命令**: `{dev['lintCommand']}`\n\n")

        # 实现顺序
        implementation_order = architecture.get("implementationOrder")
        if implementation_order:
            lines.append("## 实现顺序\n\n")
            for step in implementation_order:
                target = step.get("target", "")
                desc = step.get("description", "")
                lines.append(f"{step.get('step', '')}. **{target}** - {desc}")
                if step.get("userStoryIds"):
                    lines.append(f" (用户故事: {', '.join(step['userStoryIds'])})")
                lines.append("\n")
            lines.append("\n")

        # 注意事项
        considerations = architecture.get("considerations")
        if considerations:
            lines.append("## 考虑事项\n\n")

            security = considerations.get("security")
            if security:
                lines.append("### 安全\n\n")
                for item in security:
                    lines.append(f"- {item}\n")
                lines.append("\n")

            performance = considerations.get("performance")
            if performance:
                lines.append("### 性能\n\n")
                for item in performance:
                    lines.append(f"- {item}\n")
                lines.append("\n")

            scalability = considerations.get("scalability")
            if scalability:
                lines.append("### 可扩展性\n\n")
                for item in scalability:
                    lines.append(f"- {item}\n")
                lines.append("\n")

            maintainability = considerations.get("maintainability")
            if maintainability:
                lines.append("### 可维护性\n\n")
                for item in maintainability:
                    lines.append(f"- {item}\n")
                lines.append("\n")

        # 元数据
        metadata = architecture.get("metadata", {})
        lines.append("---\n\n")
        lines.append(f"*生成时间: {metadata.get('generatedAt', '')}*\n")
        lines.append(f"*版本: {metadata.get('version', '1.0')}*\n")

        return "".join(lines)

    def save(self, architecture: Dict[str, Any]) -> str:
        """保存架构到文件（JSON + Markdown）

        Returns:
            输出JSON文件路径
        """
        # 使用PRD文件名作为前缀
        # 保存 JSON
        output_path = f"{self.output_dir}/{self.prd_filename_prefix}.architecture.json"
        if not write_json(output_path, architecture):
            logger.error(f"保存JSON失败: {output_path}")
            return ""
        logger.info(f"架构JSON已保存到: {output_path}")

        # 保存 Markdown 预览
        md_content = self._architecture_to_markdown(architecture)
        md_path = f"{self.output_dir}/{self.prd_filename_prefix}.architecture.md"
        if write_text(md_path, md_content):
            logger.info(f"架构预览Markdown已保存到: {md_path}")
        else:
            logger.warning(f"保存Markdown预览失败: {md_path}")

        return output_path
