"""AI后端抽象基类"""

from abc import ABC, abstractmethod
from typing import List


class AIBackend(ABC):
    """AI后端抽象基类"""

    @abstractmethod
    def implement_story(self, prompt: str) -> str:
        """
        实现一个用户故事
        返回AI输出内容
        """
        pass

    @abstractmethod
    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """
        根据错误信息修复代码
        返回AI输出内容
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查AI后端是否可用
        """
        pass
