"""
Skill 注册表 - 管理所有可用的 Skill

设计模式：单例模式 + 工厂模式（和 ToolRegistry 保持一致）

注意：现在 Skill 也会同时注册到 ToolRegistry，LLM 可以直接调用 Skill！
这个 SkillRegistry 主要用于：
- 给 /skills 命令显示已加载的 Skill 列表
- 不参与工具调用流程了（全走 ToolRegistry）
"""
from typing import Dict, Type, List
from tools.base import BaseTool


class SkillRegistry:
    """
    Skill 注册表 - 全局唯一

    用途：给 /skills 命令显示已加载的 Skill 列表
    """

    # 存储所有注册的 Skill 类：{名称: Skill 类}
    _skills: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, skill_class: Type[BaseTool]) -> bool:
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
    def get(cls, name: str) -> BaseTool:
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
