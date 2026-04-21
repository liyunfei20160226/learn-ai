"""AI后端抽象基类"""

from abc import ABC, abstractmethod
from typing import List


class AIBackend(ABC):
    """AI后端抽象基类"""

    @abstractmethod
    def implement_story(self, prompt: str, write_files: bool = True) -> str:
        """
        实现一个用户故事
        返回AI输出内容
        如果write_files=True，解析代码块并写入文件（OpenAI API后端）
        """
        pass

    @abstractmethod
    def fix_errors(self, original_prompt: str, errors: List[str], target_dir: str = None) -> str:
        """
        根据错误信息修复代码
        返回AI输出内容
        target_dir: 项目根目录，用于检测实际的配置文件和版本
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查AI后端是否可用
        """
        pass
