"""
Extract embedded images from Excel files
"""

import os
import sys
from pathlib import Path
import openpyxl
from openpyxl.drawing.image import Image as XLImage

# 设置编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def extract_images_from_excel(excel_path: Path, output_dir: Path):
    """Extract all images from a single Excel file"""
    print(f"\nProcessing: {excel_path.name}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)

    image_count = 0
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        print(f"  Sheet: {sheet_name}")

        for idx, image in enumerate(ws._images):
            if isinstance(image, XLImage):
                # 获取图片数据
                img = image.ref
                if hasattr(img, 'image'):
                    image_data = img.image
                    # 创建输出文件名
                    base_name = f"{excel_path.stem}_{sheet_name}_{idx+1}"
                    ext = 'png'
                    output_path = output_dir / f"{base_name}.{ext}"

                    # 保存图片
                    with open(output_path, 'wb') as f:
                        f.write(image_data)

                    image_count += 1
                    print(f"    Extracted: {output_path.name}")

    print(f"  Total: {image_count} images")
    return image_count

def main():
    # 设计书目录
    design_dir = Path(__file__).parent / "设计书"
    # 输出目录
    output_dir = Path(__file__).parent / "extracted_images"
    output_dir.mkdir(exist_ok=True)

    total_images = 0

    # 处理所有 xlsx 文件
    for excel_file in design_dir.glob("*.xlsx"):
        if excel_file.name.startswith("~$"):  # skip temp files
            continue
        count = extract_images_from_excel(excel_file, output_dir)
        total_images += count

    print(f"\n=== Complete ===")
    print(f"Total {total_images} images extracted to: {output_dir}")

if __name__ == "__main__":
    main()
