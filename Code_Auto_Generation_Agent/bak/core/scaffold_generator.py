"""项目骨架生成器 - 先执行官方脚手架 + AI微调模式"""

import subprocess
from pathlib import Path

from config import get_config
from core.ai_backend import AIBackend
from core.architecture_loader import ArchitectureDocument
from core.template_manager import TemplateManager, get_template_manager
from utils.logger import get_logger
from utils.subprocess import run_command

logger = get_logger()
config = get_config()


def _format_backend_arch_for_ai(arch: ArchitectureDocument) -> str:
    """格式化后端架构信息供AI使用"""
    lines = []

    # 后端技术栈
    lines.append("## 后端技术栈")
    backend_stack = arch.architecture.tech_stack.backend
    for key, value in backend_stack.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")

    # 后端目录结构
    lines.append("## 后端目录结构")
    lines.append("```")
    lines.append(arch.backend.directory_structure)
    lines.append("```")
    lines.append("")

    # 后端依赖
    lines.append("## 后端依赖")
    for dep in arch.backend.dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
        if dep.description:
            lines.append(f"  说明: {dep.description}")
    lines.append("")

    # 数据模型
    lines.append("## 数据模型")
    for model in arch.backend.data_models:
        lines.append(f"### {model.name}")
        lines.append(f"- 描述: {model.description}")
        lines.append(f"- 表名/存储: {model.table_name}")
        lines.append("- 字段:")
        for field in model.fields:
            constraints = ", ".join(field.constraints)
            default_str = f" = {field.default}" if field.default else ""
            lines.append(f"  - {field.name}: {field.type} [{constraints}]{default_str}")
            if field.description:
                lines.append(f"    说明: {field.description}")
        lines.append("")

    # API端点
    lines.append("## API端点")
    for ep in arch.backend.api_endpoints:
        auth_str = "需要认证" if ep.authentication else "无需认证"
        lines.append(f"- {ep.method} {ep.path}")
        lines.append(f"  描述: {ep.description}")
        lines.append(f"  认证: {auth_str}")
    lines.append("")

    # 必须创建的文件清单（核心修复！）
    lines.append("## 必须创建的文件清单")
    lines.append("### 核心模块文件（每个都必须创建代码块！）")
    lines.append("重要：所有代码块的路径都必须以 `backend/` 开头！")
    for module in arch.backend.modules:
        lines.append(f"#### {module.name} ({module.directory})")
        for file in module.files:
            # 在路径前加上 backend/，与输出格式一致
            full_path = f"backend/{file.path}"
            lines.append(f"- `{full_path}`")
            lines.append(f"  描述: {file.description}")
            if file.dependencies:
                lines.append(f"  依赖: {', '.join(file.dependencies)}")
        lines.append("")

    # 开发配置
    lines.append("## 开发配置")
    lines.append(f"- 构建命令: {arch.backend.development.build_command}")
    lines.append(f"- 开发命令: {arch.backend.development.dev_command}")
    lines.append(f"- 测试命令: {arch.backend.development.test_command}")
    lines.append(f"- Lint命令: {arch.backend.development.lint_command}")

    return "\n".join(lines)


def _format_frontend_arch_for_ai(arch: ArchitectureDocument) -> str:
    """格式化前端架构信息供AI使用"""
    lines = []

    # 前端技术栈
    lines.append("## 前端技术栈")
    frontend_stack = arch.architecture.tech_stack.frontend
    for key, value in frontend_stack.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")

    # 前端目录结构
    lines.append("## 前端目录结构")
    lines.append("```")
    lines.append(arch.frontend.directory_structure)
    lines.append("```")
    lines.append("")

    # 前端依赖
    lines.append("## 前端依赖")
    lines.append("### 生产依赖")
    for dep in arch.frontend.dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
    lines.append("")

    lines.append("### 开发依赖")
    for dep in arch.frontend.dev_dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
    lines.append("")

    # API客户端
    lines.append("## API客户端配置")
    lines.append(f"- 基础URL: {arch.frontend.api_client.base_url}")
    lines.append("- 端点:")
    for ep in arch.frontend.api_client.endpoints:
        lines.append(f"  - {ep.name}: {ep.method} {ep.path} - {ep.description}")
    lines.append("")

    # 必须创建的文件清单（核心修复！）
    lines.append("## 必须创建的文件清单")
    lines.append("### 核心模块文件（每个都必须创建代码块！）")
    lines.append("重要：所有代码块的路径都必须以 `frontend/` 开头！")
    for module in arch.frontend.modules:
        lines.append(f"#### {module.name} ({module.directory})")
        for file in module.files:
            # 在路径前加上 frontend/，与输出格式一致
            full_path = f"frontend/{file.path}"
            lines.append(f"- `{full_path}`")
            lines.append(f"  描述: {file.description}")
            if file.dependencies:
                lines.append(f"  依赖: {', '.join(file.dependencies)}")
        lines.append("")

    # 开发配置
    lines.append("## 开发配置")
    lines.append(f"- 构建命令: {arch.frontend.development.build_command}")
    lines.append(f"- 开发命令: {arch.frontend.development.dev_command}")
    lines.append(f"- 测试命令: {arch.frontend.development.test_command}")
    lines.append(f"- Lint命令: {arch.frontend.development.lint_command}")

    return "\n".join(lines)


class ScaffoldGenerator:
    """项目骨架生成器"""

    def __init__(
        self,
        architecture: ArchitectureDocument,
        target_dir: str,
        ai_backend: AIBackend,
        template_manager: TemplateManager = None
    ):
        self.architecture = architecture
        self.target_dir = Path(target_dir)
        self.ai_backend = ai_backend
        self.template_manager = template_manager or get_template_manager()

    def _run_scaffold_commands(self, scaffold_config) -> bool:
        """执行脚手架命令"""
        if not scaffold_config or not scaffold_config.commands:
            logger.info("此框架无需执行脚手架命令，跳过")
            return True

        # 确定工作目录
        if scaffold_config.working_dir:
            work_dir = self.target_dir / scaffold_config.working_dir
            # 创建目录（如果不存在）
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = self.target_dir

        logger.info(f"工作目录: {work_dir}")

        # 依次执行命令
        for cmd in scaffold_config.commands:
            try:
                # 使用 passthrough=True 避免 Windows cp932 编码异常
                # npx/npm 输出包含特殊字符（进度条、颜色代码）
                # run_command 内部会记录日志，这里不再重复
                returncode, stdout, stderr = run_command(
                    cmd,
                    cwd=str(work_dir),
                    timeout=config.timeout.scaffold_command,
                    passthrough=True,  # 关键：透传输出到控制台
                )
                if returncode != 0:
                    logger.warning(f"命令执行返回非零值: {returncode}")
                    # 透传模式下 stderr/stdout 为空，只记录命令失败信息
                else:
                    logger.info("命令执行成功")
            except subprocess.TimeoutExpired:
                logger.error(f"命令执行超时: {cmd}")
                return False
            except Exception as e:
                logger.error(f"命令执行失败: {str(e)}")
                return False

        return True

    def generate_all(self) -> bool:
        """调用AI生成完整的项目骨架（顺序：后端 -> 前端）"""
        try:
            original_working_dir = self.ai_backend.working_dir
            self.ai_backend.working_dir = str(self.target_dir)

            # 1. 生成后端骨架
            logger.info("生成后端骨架...")
            self.generate_backend()

            # 2. 生成前端骨架
            logger.info("生成前端骨架...")
            self.generate_frontend()

            # 恢复
            self.ai_backend.working_dir = original_working_dir

            logger.info("项目骨架AI生成完成")

            # 3. 验证骨架
            validation_result = self._verify_scaffold()

            return validation_result

        except Exception as e:
            logger.error(f"生成项目骨架失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def generate_backend(self) -> bool:
        """只生成后端骨架（官方脚手架 + AI微调模式）"""
        framework = self.template_manager.detect_backend_framework(self.architecture)
        logger.info(f"检测到后端框架: {framework}")

        # 1. 执行官方脚手架命令
        scaffold_config = self.template_manager.get_backend_scaffold_commands(framework)
        if scaffold_config and scaffold_config.commands:
            logger.info(f"执行后端官方脚手架: {scaffold_config.description}")
            success = self._run_scaffold_commands(scaffold_config)
            if not success:
                logger.warning("脚手架命令执行失败，将使用AI纯生成模式")

        # 检查是否使用了通用模板（提醒用户可以贡献专用模板）
        if framework == "generic":
            detected_lang = self.architecture.architecture.tech_stack.backend.get("language", "未知")
            detected_fw = self.architecture.architecture.tech_stack.backend.get("framework", [])
            logger.warning("⚠️  未检测到专用后端模板，将使用通用模板生成")
            logger.warning(f"   检测到的语言: {detected_lang}")
            logger.warning(f"   检测到的框架: {detected_fw}")
            logger.warning("   💡 欢迎添加专用模板: prompts/backend/{framework}.md")
        else:
            hint = self.template_manager.get_backend_scaffold_hint(framework)
            if hint:
                logger.info(hint)

        prompt = self._build_backend_scaffold_prompt(framework)
        self.ai_backend.implement_story(prompt, write_files=True)
        logger.info("后端骨架生成完成")
        return True

    def generate_frontend(self) -> bool:
        """只生成前端骨架（官方脚手架 + AI微调模式）"""
        framework = self.template_manager.detect_frontend_framework(self.architecture)
        logger.info(f"检测到前端框架: {framework}")

        # 1. 执行官方脚手架命令
        scaffold_config = self.template_manager.get_frontend_scaffold_commands(framework)
        if scaffold_config and scaffold_config.commands:
            logger.info(f"执行前端官方脚手架: {scaffold_config.description}")
            success = self._run_scaffold_commands(scaffold_config)
            if not success:
                logger.warning("脚手架命令执行失败，将使用AI纯生成模式")

        # 检查是否使用了通用模板（提醒用户可以贡献专用模板）
        if framework == "generic":
            detected_lang = self.architecture.architecture.tech_stack.frontend.get("language", "未知")
            detected_fw = self.architecture.architecture.tech_stack.frontend.get("framework", [])
            logger.warning("⚠️  未检测到专用前端模板，将使用通用模板生成")
            logger.warning(f"   检测到的语言: {detected_lang}")
            logger.warning(f"   检测到的框架: {detected_fw}")
            logger.warning("   💡 欢迎添加专用模板: prompts/frontend/{framework}.md")
        else:
            hint = self.template_manager.get_frontend_scaffold_hint(framework)
            if hint:
                logger.info(hint)

        prompt = self._build_frontend_scaffold_prompt(framework)
        self.ai_backend.implement_story(prompt, write_files=True)
        logger.info("前端骨架生成完成")
        return True

    def _build_backend_scaffold_prompt(self, framework: str) -> str:
        """构建后端骨架生成提示词（根据框架选择模板）"""
        template, template_path = self.template_manager.get_backend_template(framework)
        logger.info(f"使用后端模板: {template_path}")

        # 格式化后端架构信息
        backend_arch_info = _format_backend_arch_for_ai(self.architecture)

        # 替换占位符
        prompt = template.replace("{backend_arch_info}", backend_arch_info)

        return prompt

    def _build_frontend_scaffold_prompt(self, framework: str) -> str:
        """构建前端骨架生成提示词（根据框架选择模板）"""
        template, template_path = self.template_manager.get_frontend_template(framework)
        logger.info(f"使用前端模板: {template_path}")

        # 格式化前端架构信息
        frontend_arch_info = _format_frontend_arch_for_ai(self.architecture)

        # 替换占位符
        prompt = template.replace("{frontend_arch_info}", frontend_arch_info)

        return prompt

    def _get_default_backend_template(self) -> str:
        """默认后端骨架生成模板"""
        return """你是一个后端项目初始化专家。请根据以下架构设计文档，生成完整的后端项目骨架。

=== 必须严格遵守 ===

1. 严格按照指定的目录结构创建文件
2. 严格使用指定的依赖版本
3. 严格按照指定的数据模型生成类型定义
4. 只创建骨架文件（空实现或基础实现即可）
5. 不要实现具体的业务逻辑

=== 架构设计文档 ===

{backend_arch_info}
"""

    def _get_default_frontend_template(self) -> str:
        """默认前端骨架生成模板"""
        return """你是一个前端项目初始化专家。请根据以下架构设计文档，生成完整的前端项目骨架。

=== 必须严格遵守 ===

1. 严格按照指定的目录结构创建文件
2. 严格使用指定的依赖版本
3. 严格按照指定的数据模型生成类型定义
4. 只创建骨架文件（空实现或基础实现即可）
5. 不要实现具体的业务逻辑

=== 架构设计文档 ===

{frontend_arch_info}
"""

    def _verify_scaffold(self) -> bool:
        """验证骨架是否完整生成（增强版）"""
        logger.info("验证项目骨架...")

        errors = []
        warnings = []

        # 检查后端目录是否存在
        backend_dir = self.target_dir / "backend"
        if backend_dir.exists():
            logger.info("✓ 后端目录存在")
        else:
            errors.append("后端目录不存在")

        # 检查前端目录是否存在
        frontend_dir = self.target_dir / "frontend"
        if frontend_dir.exists():
            logger.info("✓ 前端目录存在")
        else:
            errors.append("前端目录不存在")

        # 检查关键配置文件
        pyproject = self.target_dir / "backend" / "pyproject.toml"
        if pyproject.exists():
            logger.info("✓ pyproject.toml 存在")
        else:
            errors.append("backend/pyproject.toml 不存在")

        package_json = self.target_dir / "frontend" / "package.json"
        if package_json.exists():
            logger.info("✓ package.json 存在")
        else:
            errors.append("frontend/package.json 不存在")

        # 核心修复：检查架构文档中定义的所有后端文件
        if backend_dir.exists() and self.architecture.backend.modules:
            logger.info("检查后端模块文件完整性...")
            for module in self.architecture.backend.modules:
                for file in module.files:
                    # 架构文档的路径是相对 backend 目录的（如 app/core/config.py）
                    file_path = self.target_dir / "backend" / file.path
                    if file_path.exists():
                        logger.info(f"✓ backend/{file.path} 存在")
                    else:
                        errors.append(f"文件缺失: backend/{file.path}")

        # 核心修复：检查架构文档中定义的所有前端文件
        if frontend_dir.exists() and self.architecture.frontend.modules:
            logger.info("检查前端模块文件完整性...")
            for module in self.architecture.frontend.modules:
                for file in module.files:
                    # 架构文档的路径是相对 frontend 目录的（如 app/page.tsx）
                    file_path = self.target_dir / "frontend" / file.path
                    if file_path.exists():
                        logger.info(f"✓ frontend/{file.path} 存在")
                    else:
                        warnings.append(f"前端文件缺失: frontend/{file.path} (可能由脚手架自动创建)")

        # 输出验证结果
        if warnings:
            logger.warning("骨架验证发现以下警告（非致命）:")
            for warn in warnings:
                logger.warning(f"  - {warn}")

        if errors:
            logger.error("❌ 骨架验证发现以下错误:")
            for err in errors:
                logger.error(f"  - {err}")
            return False
        else:
            logger.info("✅ 骨架验证通过（所有定义的文件都已创建）")
            return True
