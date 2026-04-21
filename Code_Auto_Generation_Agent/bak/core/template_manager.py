"""
提示词模板管理器 - 根据技术栈自动选择合适的骨架生成模板

支持的功能：
1. 根据后端框架自动选择对应模板 (FastAPI/Spring Boot/Gin/...)
2. 根据前端框架自动选择对应模板 (Next.js/Vue/React/...)
3. 提供脚手架命令建议（如 npm create next-app@latest, uv add fastapi 等）
4. 模板回退机制（找不到特定模板时使用通用模板）
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import config
from core.architecture_loader import ArchitectureDocument


@dataclass
class ScaffoldCommand:
    """脚手架命令配置"""
    commands: list[str]  # 按顺序执行的命令列表
    description: str
    working_dir: str = ""  # 子目录（如 backend/ frontend/）

    @classmethod
    def from_dict(cls, data: Dict) -> 'ScaffoldCommand':
        """从字典配置创建 ScaffoldCommand"""
        return cls(
            commands=data.get("commands", []),
            description=data.get("description", ""),
            working_dir=data.get("working_dir", "")
        )


# 从 config 模块加载配置
BACKEND_FRAMEWORK_MAPPING = config.BACKEND_FRAMEWORK_MAPPING
FRONTEND_FRAMEWORK_MAPPING = config.FRONTEND_FRAMEWORK_MAPPING

# 将 config 中的字典配置转换为 ScaffoldCommand 对象
BACKEND_SCAFFOLD_COMMANDS: Dict[str, ScaffoldCommand] = {
    key: ScaffoldCommand.from_dict(value)
    for key, value in config.BACKEND_SCAFFOLD_COMMANDS.items()
}

FRONTEND_SCAFFOLD_COMMANDS: Dict[str, ScaffoldCommand] = {
    key: ScaffoldCommand.from_dict(value)
    for key, value in config.FRONTEND_SCAFFOLD_COMMANDS.items()
}


class TemplateManager:
    """提示词模板管理器"""

    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            self.prompts_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "prompts"
            )
        else:
            self.prompts_dir = prompts_dir

    def detect_backend_framework(self, arch: ArchitectureDocument) -> str:
        """
        从架构文档中检测后端框架类型

        返回: 框架标识 (fastapi, spring-boot, gin, generic 等)
        """
        backend_stack = arch.architecture.tech_stack.backend

        # 从 framework 字段中检测
        frameworks = backend_stack.get("framework", [])
        if isinstance(frameworks, str):
            frameworks = [frameworks]

        for fw in frameworks:
            fw_lower = fw.lower().strip()
            for keyword, template_name in BACKEND_FRAMEWORK_MAPPING.items():
                if keyword in fw_lower:
                    return template_name

        # 从 language 字段中检测
        language = backend_stack.get("language", "").lower()
        if "python" in language:
            return "fastapi"  # 默认 Python 使用 FastAPI
        if "java" in language:
            return "spring-boot"  # 默认 Java 使用 Spring Boot
        if "go" in language:
            return "gin"  # 默认 Go 使用 Gin

        return "generic"

    def detect_frontend_framework(self, arch: ArchitectureDocument) -> str:
        """
        从架构文档中检测前端框架类型

        返回: 框架标识 (nextjs, vue, react, generic 等)
        """
        frontend_stack = arch.architecture.tech_stack.frontend

        # 从 framework 字段中检测
        frameworks = frontend_stack.get("framework", [])
        if isinstance(frameworks, str):
            frameworks = [frameworks]

        for fw in frameworks:
            fw_lower = fw.lower().strip()
            for keyword, template_name in FRONTEND_FRAMEWORK_MAPPING.items():
                if keyword in fw_lower:
                    return template_name

        return "generic"

    def get_backend_template(self, framework: str) -> Tuple[str, str]:
        """
        获取后端模板内容

        返回: (模板内容, 模板路径)
        """
        # 优先使用特定模板
        template_path = os.path.join(self.prompts_dir, "backend", f"{framework}.md")

        # 如果不存在，使用通用模板
        if not os.path.exists(template_path):
            template_path = os.path.join(self.prompts_dir, "backend", "generic.md")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read(), template_path

    def get_frontend_template(self, framework: str) -> Tuple[str, str]:
        """
        获取前端模板内容

        返回: (模板内容, 模板路径)
        """
        # 优先使用特定模板
        template_path = os.path.join(self.prompts_dir, "frontend", f"{framework}.md")

        # 如果不存在，使用通用模板
        if not os.path.exists(template_path):
            template_path = os.path.join(self.prompts_dir, "frontend", "generic.md")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read(), template_path

    def get_backend_scaffold_hint(self, framework: str) -> Optional[str]:
        """获取后端脚手架命令提示（可选）"""
        cmd = BACKEND_SCAFFOLD_COMMANDS.get(framework)
        if cmd and cmd.commands:
            return f"💡 {cmd.description}: `{cmd.commands[0]}`"
        return None

    def get_frontend_scaffold_hint(self, framework: str) -> Optional[str]:
        """获取前端脚手架命令提示（可选）"""
        cmd = FRONTEND_SCAFFOLD_COMMANDS.get(framework)
        if cmd and cmd.commands:
            return f"💡 {cmd.description}: `{cmd.commands[0]}`"
        return None

    def get_backend_scaffold_commands(self, framework: str) -> Optional[ScaffoldCommand]:
        """获取后端脚手架命令配置（用于实际执行）"""
        return BACKEND_SCAFFOLD_COMMANDS.get(framework)

    def get_frontend_scaffold_commands(self, framework: str) -> Optional[ScaffoldCommand]:
        """获取前端脚手架命令配置（用于实际执行）"""
        return FRONTEND_SCAFFOLD_COMMANDS.get(framework)


# 单例实例
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """获取模板管理器单例"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
