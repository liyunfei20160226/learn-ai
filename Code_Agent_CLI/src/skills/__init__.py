"""
Skill 系统 - 兼容 Claude 官方 Skill 格式

核心设计理念（和 Claude Code 一致）：
- Skill = 目录 + SKILL.md
- SKILL.md 包含：YAML frontmatter + Markdown 使用指南
- Skill 本质是给 LLM 看的"操作手册"，在需要时注入上下文

📦 自动发现机制：
只要把 Skill 目录（包含 SKILL.md）放到项目根目录的 skills/ 下，就会自动被发现和加载！
不需要修改任何代码，不需要手动注册。

目录结构：
    Code_Agent_CLI/
    ├── src/
    │   └── skills/          ← 基础设施（基类、加载器、注册表）
    │       ├── base.py
    │       ├── registry.py
    │       ├── loader.py
    │       └── __init__.py
    └── skills/              ← 用户 Skill 存放目录
        ├── analyze_project/
        │   └── SKILL.md
        ├── docx/
        │   └── SKILL.md
        └── ...

创建新 Skill 的方法：
1. 在项目根目录 skills/ 下新建目录：my_skill/
2. 在目录中新建 SKILL.md 文件
3. 按照格式填写：
    ---
    name: my_skill
    description: "触发条件描述..."
    license: MIT
    ---

    # Skill 标题
    详细的使用指南和步骤...
"""
from .base import BaseSkill, SkillContext, SkillError
from .registry import SkillRegistry
from .loader import load_all_skills

# Skill 依赖工具，先确保所有工具已注册
from tools.loader import register_all_tools
register_all_tools()

# 🚀 自动加载所有 Skill（不需要手动注册了！）
load_all_skills()

__all__ = [
    "BaseSkill",
    "SkillContext",
    "SkillError",
    "SkillRegistry",
    "load_all_skills",
]
