"""
PDF文本提取器 - 从PDF提取纯文本
用于纯文本PDF可以直接提取，不需要走视觉模型
"""
import pypdf
from pathlib import Path
from typing import Tuple


class PDFTextExtractor:
    """从PDF提取纯文本"""

    def extract(self, pdf_path: Path) -> Tuple[bool, str, int]:
        """
        提取PDF所有文本
        :return: (success, extracted_text, page_count)
        """
        if not pdf_path.exists():
            return False, f"File not found: {pdf_path}", 0

        try:
            text_parts = []
            with open(pdf_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                page_count = len(reader.pages)

                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

            full_text = "\n\n".join(text_parts)
            return True, full_text, page_count

        except Exception as e:
            return False, str(e), 0
