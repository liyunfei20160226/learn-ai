"""提示词模板管理"""

import os
from typing import List, Optional

from core.architecture_loader import ArchitectureDocument, format_architecture_context_for_story
from core.story_manager import StoryState
from utils.file_utils import read_file
from utils.logger import get_logger

logger = get_logger()


def get_implementation_prompt(
    story: StoryState,
    project_description: str,
    lessons_learned: List[str],
    target_dir: str,
    architecture: Optional[ArchitectureDocument] = None,
    dependency_code: str = ""
) -> str:
    """获取实现用户故事的prompt

    Args:
        dependency_code: 依赖任务已生成的完整代码，用于确保接口一致性
    """

    template_path = os.path.join(os.path.dirname(__file__), "implement-story.md")
    template = read_file(template_path)
    if not template:
        logger.error(f"提示词模板找不到: {template_path}")
        template = DEFAULT_TEMPLATE

    # 填充验收标准
    acceptance_text = "\n".join(f"- {ac}" for ac in story.acceptance_criteria)

    # 填充经验教训
    lessons_text = ""
    if lessons_learned:
        lessons_text = "\n# 之前迭代的经验教训\n\n"
        for lesson in lessons_learned[-5:]:  # 只取最近5条
            lessons_text += f"- {lesson}\n"

    # 获取当前项目代码结构摘要
    project_tree = _get_project_tree(target_dir)
    tree_text = ""
    if project_tree:
        tree_text = f"\n# 当前项目目录结构\n\n```\n{project_tree}\n```\n"

    # 填充架构上下文
    arch_text = ""
    if architecture:
        arch_text = "\n" + format_architecture_context_for_story(architecture)
        arch_text += "\n"

    # 获取当前环境信息
    env_info = _get_env_info(target_dir)

    # 替换占位符
    prompt = template.replace("{{PROJECT_DESCRIPTION}}", project_description)
    prompt = prompt.replace("{{STORY_ID}}", story.id)
    prompt = prompt.replace("{{STORY_TITLE}}", story.title)
    prompt = prompt.replace("{{STORY_DESCRIPTION}}", story.description)
    prompt = prompt.replace("{{ACCEPTANCE_CRITERIA}}", acceptance_text)
    prompt = prompt.replace("{{LESSONS_LEARNED}}", lessons_text)
    prompt = prompt.replace("{{PROJECT_TREE}}", tree_text)
    prompt = prompt.replace("{{ENV_INFO}}", env_info)
    prompt = prompt.replace("{{DEPENDENCY_CODE}}", dependency_code)

    # 在项目描述后插入架构上下文
    # 找一个合适的位置插入，比如在 "## 当前要实现的用户故事" 之前
    if arch_text and "## 当前要实现的用户故事" in prompt:
        prompt = prompt.replace("## 当前要实现的用户故事", f"{arch_text}\n## 当前要实现的用户故事")

    return prompt


def get_fix_errors_prompt(target_dir: str = None) -> str:
    """获取修复错误的prompt（可选：添加实际环境信息）

    注意：{{FILE_CONTENTS}} 和 {{ORIGINAL_PROMPT}}、{{ERROR_LIST}} 占位符
    由调用方在具体修复时替换，因为文件内容需要从错误信息中动态提取
    """
    template_path = os.path.join(os.path.dirname(__file__), "fix-errors.md")
    template = read_file(template_path)
    if not template:
        return DEFAULT_FIX_TEMPLATE

    # 添加实际环境信息
    env_info = ""
    if target_dir:
        env_info = _get_env_info(target_dir)

    template = template.replace("{{ENV_INFO}}", env_info)
    return template


def _get_env_info(target_dir: str) -> str:
    """获取当前环境的完整信息，明确告诉AI实际情况，让它从源头就不输出错误内容"""
    import json
    import sys

    info = []
    info.append("## 📍 当前环境信息")
    info.append(f"- Python 版本: {sys.version.split()[0]}")
    info.append("- 包管理器: uv")
    info.append(f"- 操作系统: {sys.platform}")
    info.append("")

    # Python 兼容性约束（总是提醒）
    info.append("## ⚠️ Python 兼容性约束")
    info.append("- 不要创建 .python-version 文件（会导致版本不兼容）")
    info.append(f"- pyproject.toml 的 requires-python 必须兼容 Python {sys.version.split()[0]}")
    info.append("- 建议设置为 '>=3.10'")
    info.append("")

    # 检测前端配置
    frontend_dir = os.path.join(target_dir, 'frontend')
    if os.path.exists(frontend_dir):
        info.append("## 📍 前端实际情况")

        # ESLint 版本
        pkg_json = os.path.join(frontend_dir, 'package.json')
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                eslint_version = pkg.get('devDependencies', {}).get('eslint') or pkg.get('dependencies', {}).get('eslint')
                if eslint_version:
                    info.append(f"- ESLint 版本: {eslint_version}")
            except Exception:
                pass

        # 存在哪些配置文件
        config_files = []
        for f in sorted(os.listdir(frontend_dir)):
            if f.startswith('.eslintrc') or f.startswith('eslint.config'):
                config_files.append(f)
        if config_files:
            info.append(f"- 已存在的 ESLint 配置文件: {', '.join(config_files)}")
            info.append("- ⚠️ 重要：只修改上面列出的配置文件，不要创建新的！")
            if any('eslint.config' in f for f in config_files):
                info.append("- 注意：eslint.config.js/mjs 是 flat config 格式（ESLint 9+）")
                info.append("  不要去修改不存在的 .eslintrc.js 文件！")
        info.append("")

    return "\n".join(info)


def get_build_commands_prompt(
    project_description: str,
    target_dir: str
) -> str:
    """获取询问构建命令的prompt"""
    template_path = os.path.join(os.path.dirname(__file__), "get-build-commands.md")
    template = read_file(template_path)
    if not template:
        logger.error(f"提示词模板找不到: {template_path}")
        return ""

    # 获取当前项目目录结构
    project_tree = _get_project_tree(target_dir)
    tree_text = ""
    if project_tree:
        tree_text = f"\n## 当前项目目录结构\n\n```\n{project_tree}\n```\n"

    # 获取当前环境信息
    env_info = _get_env_info(target_dir)

    prompt = template.replace("{{PROJECT_DESCRIPTION}}", project_description)
    prompt = prompt.replace("{{PROJECT_TREE}}", tree_text)
    prompt = prompt.replace("{{ENV_INFO}}", env_info)

    return prompt


def _get_project_tree(target_dir: str) -> str:
    """获取项目目录树"""
    try:
        import subprocess
        # 排除 .venv, node_modules, .git, __pycache__ 等目录
        result = subprocess.run(
            "find . \\( -path '*/.venv/*' -o -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/__pycache__/*' \\) -prune -o \\( -type f \\( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.html' -o -name '*.css' -o -name '*.go' -o -name '*.rs' -o -name '*.toml' -o -name '*.json' -o -name '*.md' \\) \\) -print | head -50",
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return ""


DEFAULT_TEMPLATE = """# 代码自动生成 - 实现用户故事

## 项目描述

{{PROJECT_DESCRIPTION}}

## 当前要实现的用户故事

**{{STORY_ID}}: {{STORY_TITLE}}**

{{STORY_DESCRIPTION}}

## 验收标准

{{ACCEPTANCE_CRITERIA}}

{{PROJECT_TREE}}

{{LESSONS_LEARNED}}

## 任务

请实现上述用户故事。遵循项目现有的代码风格和架构。修改必要的文件，添加新功能代码。确保代码能正常工作并且通过所有验收标准。

工作目录是当前目录。所有路径都是相对路径。
"""

DEFAULT_FIX_TEMPLATE = """# 修复错误

上面的实现有以下错误，请修复：
"""
