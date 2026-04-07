"""
文档转换器基类
"""
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, List


class ConversionResult(BaseModel):
    """转换结果"""
    success: bool = Field(description="是否成功")
    output_path: Optional[Path] = Field(default=None, description="输出文件路径")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    page_count: int = Field(default=0, description="页数")


class ImageExtractionResult(BaseModel):
    """图片提取结果"""
    success: bool = Field(description="是否成功")
    image_paths: List[Path] = Field(default_factory=list, description="输出图片路径列表")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class DocumentConverter(ABC):
    """文档转换器基类"""

    @abstractmethod
    def convert(self, input_path: Path, output_dir: Path) -> ConversionResult:
        """转换文档
        :param input_path: 输入文件路径
        :param output_dir: 输出目录
        :return: 转换结果
        """
        pass

    @abstractmethod
    def can_convert(self, input_path: Path) -> bool:
        """判断是否能转换该文件"""
        pass
