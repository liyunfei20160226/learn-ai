"""
Skill 自动加载器 - 兼容 Claude 官方 Skill 格式

设计理念（和 Claude Code 一致）：
- Skill = 目录 + SKILL.md
- SKILL.md 包含：YAML frontmatter + Markdown 使用指南
- Skill 本质是给 LLM 看的"操作手册"，在需要时注入上下文

架构改造：Skill 现在直接作为 Tool 注册到 ToolRegistry！
- LLM 自己决定什么时候调用哪个 Skill
- 不再需要 skill_ 前缀和特殊判断逻辑
- 统一的工具调用机制
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any

from tools.base import BaseTool
from .registry import SkillRegistry
from tools.registry import ToolRegistry


class OfficialSkill(BaseTool):
    """
    官方 Skill 包装类

    把官方格式的 Skill（目录 + SKILL.md）适配成 BaseTool 接口
    这样 Skill 就可以直接被 LLM 调用，和普通工具没有区别！
    """

    def __init__(self, skill_dir: str):
        self.skill_dir = Path(skill_dir)
        self.skill_md_path = self.skill_dir / "SKILL.md"
        self._parse_skill_md()

    def _parse_skill_md(self):
        """解析 SKILL.md，提取 YAML frontmatter 和 Markdown 内容"""
        with open(self.skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取 YAML frontmatter (--- 之间的内容)
        pattern = r'^---\n(.*?)\n---\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if match:
            frontmatter_str = match.group(1)
            self._content = match.group(2).strip()

            # 简单解析 YAML
            try:
                import yaml
                frontmatter = yaml.safe_load(frontmatter_str)
                self._name = frontmatter.get('name', self.skill_dir.name)
                self._description = frontmatter.get('description', '')
                self._license = frontmatter.get('license', '')
            except Exception:  # noqa: BLE001
                self._name = self.skill_dir.name
                self._description = f"Skill: {self.skill_dir.name}"
                self._content = content
        else:
            self._name = self.skill_dir.name
            self._description = f"Skill: {self.skill_dir.name}"
            self._content = content

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def tool_type(self) -> str:
        """Skill 类型，使用更大的阈值来避免操作手册被截断"""
        return "skill"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户的具体请求（可选）",
                    "default": "",
                },
            },
            "required": [],
        }

    async def run(self, args: Dict[str, Any]) -> str:
        """
        核心机制：把 Skill 的使用指南返回给 LLM

        这就是 Claude Code 的做法：Skill 不是代码执行，而是上下文注入！
        """
        query = args.get('query', '')

        result = f"""
=== 已启用 Skill: {self._name} ===

下面是这个 Skill 的完整使用指南，请仔细阅读并按照指南处理用户的请求：

{self._content}

"""

        # 如果有 scripts/ 目录，告诉 LLM 有脚本可用
        scripts_dir = self.skill_dir / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.py")) + list(scripts_dir.glob("*.js"))
            if scripts:
                result += "\n=== 可用脚本 ===\n"
                for script in scripts:
                    rel_path = script.relative_to(self.skill_dir)
                    result += f"- {rel_path}\n"

        if query:
            result += f"\n=== 用户请求 ===\n{query}\n"

        return result


class SkillLoader:
    """
    Skill 自动加载器（Claude 官方格式兼容）

    自动扫描目录下所有子目录，找到包含 SKILL.md 的目录并加载
    """

    @classmethod
    def load_all(cls, skills_dir: str = None) -> List[str]:
        """
        自动加载所有官方格式的 Skill，并直接注册到 ToolRegistry

        Args:
            skills_dir: Skill 所在目录，默认是项目根目录下的 skills/ 目录

        Returns:
            已加载的 Skill 名称列表
        """
        if skills_dir is None:
            # 默认：项目根目录下的 skills/ 目录（不是 src/skills/）
            # src/skills/ 是基础设施，skills/ 是用户存放 Skill 的地方
            current_dir = os.path.dirname(os.path.abspath(__file__))  # src/skills/
            src_dir = os.path.dirname(current_dir)  # src/
            project_root = os.path.dirname(src_dir)  # 项目根目录
            skills_dir = os.path.join(project_root, "skills")

        skills_path = Path(skills_dir)
        loaded_skills = []

        print(f"📂 Skill 目录: {skills_path}")
        print()
        print("🔍 扫描目录型 Skill（Claude 官方兼容格式）...")

        # 扫描所有包含 SKILL.md 的子目录
        for item in skills_path.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    try:
                        skill_dir = str(item)

                        # 先实例化获取名称
                        skill = OfficialSkill(skill_dir)
                        skill_name = skill.name

                        # 检查是否已注册（检查 ToolRegistry）
                        if skill_name in ToolRegistry.list_names():
                            print(f"  ⏭️  跳过 Skill: {skill_name} (已注册为 Tool)")
                            continue

                        # 动态创建包装类（因为注册表需要的是类，不是实例）
                        class WrapperSkill(BaseTool):
                            name = skill.name
                            description = skill.description
                            tool_type = skill.tool_type  # ✅ 传递工具类型标记
                            input_schema = skill.input_schema

                            async def run(self, args):
                                s = OfficialSkill(skill_dir)
                                return await s.run(args)

                        # 🎯 直接注册到 ToolRegistry！Skill 现在就是 Tool！
                        ToolRegistry.register(WrapperSkill)
                        # 同时也注册到 SkillRegistry（给 /skills 命令显示用）
                        SkillRegistry.register(WrapperSkill)

                        loaded_skills.append(skill_name)
                        print(f"  ✅ 加载 Skill: {skill_name} (已注册为 Tool)")

                    except Exception as e:
                        print(f"  ❌ 加载目录 Skill {item.name} 失败: {e}")

        return loaded_skills


def load_all_skills(skills_dir: str = None) -> List[str]:
    """
    自动加载所有 Skill（便捷函数）

    使用示例：
        from skills.loader import load_all_skills
        load_all_skills()  # 自动发现并注册所有 Skill
    """
    print()
    print("=" * 60)
    print("🔍 正在扫描并加载 Skill...")
    print("=" * 60)

    loaded = SkillLoader.load_all(skills_dir)

    print()
    print(f"✅ 共加载 {len(loaded)} 个 Skill")
    print(f"   Skill 列表: {', '.join(loaded)}")
    print("=" * 60)
    print()

    return loaded
