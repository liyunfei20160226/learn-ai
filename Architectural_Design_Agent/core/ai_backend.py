"""AI后端抽象基类"""
from abc import ABC, abstractmethod
from typing import Optional


class AIBackend(ABC):
    """AI后端抽象基类"""

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用"""
        pass

    @abstractmethod
    def generate(self, prompt: str) -> Optional[str]:
        """调用AI生成内容

        Args:
            prompt: 输入prompt

        Returns:
            AI生成的内容，失败返回None
        """
        pass
