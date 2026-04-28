"""
Skill 注册表 - 管理所有可用的 Skill

设计模式：单例模式 + 工厂模式（和 ToolRegistry 保持一致）
"""
from typing import Dict, Type, List
from .base import BaseSkill


class SkillRegistry:
    """
    Skill 注册表 - 全局唯一

    使用方法：
        # 注册
        SkillRegistry.register(AnalyzeProjectSkill)

        # 查找
        skill = SkillRegistry.get("analyze_project")

        # 执行
        result = await skill.execute(args, context)
    """

    # 存储所有注册的 Skill 类：{名称: Skill 类}
    _skills: Dict[str, Type[BaseSkill]] = {}

    @classmethod
    def register(cls, skill_class: Type[BaseSkill]) -> bool:
        """
        注册一个 Skill 类（幂等：重复注册不报错）

        Args:
            skill_class: Skill 类（不是实例！是类本身）

        Returns:
            bool: 新注册成功返回 True，已存在返回 False
        """
        dummy = skill_class()
        name = dummy.name

        if name in cls._skills:
            return False  # 已存在，静默跳过

        cls._skills[name] = skill_class
        return True

    @classmethod
    def get(cls, name: str) -> BaseSkill:
        """
        根据名称获取 Skill 实例

        Args:
            name: Skill 名称

        Returns:
            Skill 实例

        Raises:
            ValueError: 如果 Skill 不存在
        """
        if name not in cls._skills:
            raise ValueError(f"Skill 不存在：{name}")

        skill_class = cls._skills[name]
        return skill_class()

    @classmethod
    def list_names(cls) -> List[str]:
        """获取所有已注册的 Skill 名称"""
        return list(cls._skills.keys())

    @classmethod
    def get_descriptions(cls) -> List[Dict]:
        """
        获取所有已注册 Skill 的描述，格式符合 LLM tool call 要求

        这样 Agent 就能像调用普通工具一样调用 Skill！
        """
        descriptions = []
        for name in cls._skills.keys():
            skill = cls.get(name)
            descriptions.append({
                "name": f"skill_{skill.name}",  # 加 skill_ 前缀，和普通工具区分
                "description": skill.description,
                "input_schema": skill.input_schema,
            })
        return descriptions

    @classmethod
    def is_skill_call(cls, tool_name: str) -> bool:
        """
        判断是不是一个 Skill 调用

        Args:
            tool_name: 工具调用的名称

        Returns:
            bool: 如果是 Skill 调用返回 True
        """
        return tool_name.startswith("skill_")

    @classmethod
    def extract_skill_name(cls, tool_name: str) -> str:
        """
        从工具调用名称中提取 Skill 名称

        Args:
            tool_name: 工具调用名称，如 "skill_analyze_project"

        Returns:
            Skill 名称，如 "analyze_project"
        """
        if not cls.is_skill_call(tool_name):
            raise ValueError(f"不是 Skill 调用：{tool_name}")

        return tool_name[len("skill_"):]
