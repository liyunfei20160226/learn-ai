"""提示词模板管理"""

import os
from typing import List

from core.story_manager import StoryState
from utils.file_utils import read_file
from utils.logger import get_logger

logger = get_logger()


def get_implementation_prompt(
    story: StoryState,
    project_description: str,
    lessons_learned: List[str],
    target_dir: str
) -> str:
    """获取实现用户故事的prompt"""

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

    # 替换占位符
    prompt = template.replace("{{PROJECT_DESCRIPTION}}", project_description)
    prompt = prompt.replace("{{STORY_ID}}", story.id)
    prompt = prompt.replace("{{STORY_TITLE}}", story.title)
    prompt = prompt.replace("{{STORY_DESCRIPTION}}", story.description)
    prompt = prompt.replace("{{ACCEPTANCE_CRITERIA}}", acceptance_text)
    prompt = prompt.replace("{{LESSONS_LEARNED}}", lessons_text)
    prompt = prompt.replace("{{PROJECT_TREE}}", tree_text)

    return prompt


def get_fix_errors_prompt() -> str:
    """获取修复错误的prompt"""
    template_path = os.path.join(os.path.dirname(__file__), "fix-errors.md")
    template = read_file(template_path)
    if not template:
        return DEFAULT_FIX_TEMPLATE
    return template


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

    prompt = template.replace("{{PROJECT_DESCRIPTION}}", project_description)
    prompt = prompt.replace("{{PROJECT_TREE}}", tree_text)

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
