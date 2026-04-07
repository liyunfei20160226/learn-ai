"""
LibreOffice 转换器 - 将各种文档格式转换为PDF
支持: docx, doc, xlsx, xls, pptx, ppt, odt, ods, odp 等
"""
import subprocess
import shutil
from pathlib import Path
from typing import List

from .base import DocumentConverter, ConversionResult


# 支持转换的扩展名
SUPPORTED_EXTENSIONS = {
    ".docx", ".doc",
    ".xlsx", ".xls",
    ".pptx", ".ppt",
    ".odt", ".ods", ".odp",
    ".rtf", ".csv", ".html",
}


class LibreOfficeConverter(DocumentConverter):
    """使用LibreOffice命令行转换文档为PDF"""

    def __init__(self):
        self._libreoffice_path = self._find_libreoffice()

    def _find_libreoffice(self) -> str | None:
        """查找系统中的LibreOffice可执行文件"""
        candidates = [
            "libreoffice",
            "soffice",
            "/usr/bin/libreoffice",
            "/usr/local/bin/libreoffice",
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
            "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
        ]
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        return None

    def is_available(self) -> bool:
        """检查LibreOffice是否可用"""
        return self._libreoffice_path is not None

    def can_convert(self, input_path: Path) -> bool:
        """判断是否能转换"""
        ext = input_path.suffix.lower()
        return ext in SUPPORTED_EXTENSIONS and self.is_available()

    def get_supported_extensions(self) -> List[str]:
        """获取支持的扩展名列表"""
        return sorted(SUPPORTED_EXTENSIONS)

    def convert(self, input_path: Path, output_dir: Path) -> ConversionResult:
        """转换文档为PDF"""
        if not self.is_available():
            return ConversionResult(
                success=False,
                error_message="LibreOffice not found in system PATH. Please install LibreOffice first."
            )

        if not input_path.exists():
            return ConversionResult(
                success=False,
                error_message=f"Input file not found: {input_path}"
            )

        # 创建输出目录
        output_dir.mkdir(parents=True, exist_ok=True)

        # 输出PDF文件名 = 原文件名.pdf
        output_filename = input_path.stem + ".pdf"
        output_path = output_dir / output_filename

        try:
            # 调用LibreOffice命令行转换
            cmd = [
                self._libreoffice_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(input_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                return ConversionResult(
                    success=False,
                    error_message=f"LibreOffice conversion failed: {result.stderr}"
                )

            # 检查输出文件是否生成
            # LibreOffice默认输出到outdir，文件名就是stem.pdf
            if not output_path.exists():
                # 有时候可能输出名字不对，找找看
                possible_outputs = list(output_dir.glob("*.pdf"))
                if possible_outputs:
                    output_path = possible_outputs[0]
                else:
                    return ConversionResult(
                        success=False,
                        error_message="LibreOffice finished but no PDF output file found"
                    )

            return ConversionResult(
                success=True,
                output_path=output_path,
                page_count=0  # 后续提取时会统计页数
            )

        except subprocess.TimeoutExpired:
            return ConversionResult(
                success=False,
                error_message="LibreOffice conversion timed out after 5 minutes"
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                error_message=f"Conversion failed with exception: {str(e)}"
            )
