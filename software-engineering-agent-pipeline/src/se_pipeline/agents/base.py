"""
Agent 基类 - 所有阶段Agent的抽象接口
"""
from abc import ABC, abstractmethod

from ..types.pipeline import PipelineState


class BaseAgent(ABC):
    """所有Agent的基类"""

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """执行Agent逻辑，返回更新后的状态"""
        pass

    def name(self) -> str:
        """Agent名称"""
        return self.__class__.__name__
