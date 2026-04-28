"""
Skill 基类 - 定义所有 Skill 的统一接口

Skill vs Tool 的区别：
- Tool: 原子操作，一次调用完成（如读一个文件）
- Skill: 复合能力，内部可以多轮调用工具，有自己的工作流程（如分析整个项目）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from dataclasses import dataclass

from llm.base import LLMProvider


@dataclass
class SkillContext:
    """Skill 执行时的上下文环境"""
    llm: LLMProvider  # Skill 可以用自己的 LLM 调用
    tool_registry: Any  # Skill 内部可以调用工具
    working_dir: str = "."  # 工作目录


class BaseSkill(ABC):
    """
    所有 Skill 的抽象基类

    每个具体的 Skill 都必须继承这个类，并实现以下属性和方法：
    - name: Skill 名称（必须是唯一的）
    - description: Skill 描述（告诉 Agent 什么时候用这个 Skill）
    - input_schema: Skill 参数的 JSON Schema
    - async execute(): 执行 Skill 逻辑（内部可以多轮调用工具）
    """

    # ========== 子类必须实现这些属性 ==========

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill 名称（必须唯一）"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Skill 描述（给 Agent 看的，告诉它什么时候用这个 Skill）

        描述应该包含：
        1. 这个 Skill 是做什么的
        2. 什么时候应该用它（用户说什么关键词时用）
        3. 用它有什么好处（比如：比你自己一个个文件读快很多）

        示例：
        "快速分析整个项目结构，自动识别项目类型、技术栈、关键文件。
        当用户说'看看这个项目'、'了解一下结构'、'分析项目'时用。
        不要自己慢慢一个个文件读，直接用这个 Skill 一次性拿到完整分析。"
        """
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """
        Skill 参数的 JSON Schema

        返回格式示例：
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径"},
            },
            "required": ["path"]
        }
        """
        pass

    # ========== 子类必须实现这个方法 ==========

    @abstractmethod
    async def execute(self, args: Dict[str, Any], context: SkillContext) -> str:
        """
        执行 Skill 的核心逻辑

        重要：
        1. 内部可以多轮调用工具（通过 context.tool_registry）
        2. 内部可以自己调用 LLM（通过 context.llm）
        3. 返回最终结果字符串

        Args:
            args: Skill 参数字典
            context: 执行上下文，包含 LLM 和 Tool 访问能力

        Returns:
            Skill 执行结果字符串
        """
        pass

    # ========== 所有 Skill 共用的方法 ==========

    def __str__(self) -> str:
        """方便打印调试"""
        return f"<Skill {self.name}: {self.description}>"

    def __repr__(self) -> str:
        return self.__str__()


class SkillError(Exception):
    """Skill 执行失败的异常"""
    pass
