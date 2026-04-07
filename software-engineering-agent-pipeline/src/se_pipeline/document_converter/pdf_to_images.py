"""
PDF转图片转换器 - 将PDF逐页转换为高清图片，供视觉模型解析
"""
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
from typing import List

from .base import ImageExtractionResult


class PDFToImageConverter:
    """将PDF逐页转换为图片"""

    def __init__(self, dpi: int = 300):
        """
        :param dpi: 输出图片DPI，300足够高清识别
        """
        self.dpi = dpi

    def convert(self, pdf_path: Path, output_dir: Path) -> ImageExtractionResult:
        """将PDF逐页转换为图片"""
        if not pdf_path.exists():
            return ImageExtractionResult(
                success=False,
                error_message=f"PDF file not found: {pdf_path}"
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            doc = fitz.open(pdf_path)
            image_paths: List[Path] = []

            # 缩放因子，DPI转缩放比例
            zoom = self.dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)

            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(matrix=matrix)
                output_filename = f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
                output_path = output_dir / output_filename

                # 保存PNG
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.save(output_path, "PNG")
                image_paths.append(output_path)

            doc.close()

            return ImageExtractionResult(
                success=True,
                image_paths=image_paths
            )

        except Exception as e:
            return ImageExtractionResult(
                success=False,
                error_message=f"PDF to image conversion failed: {str(e)}"
            )
