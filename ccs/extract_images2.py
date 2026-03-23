"""
Extract embedded images from Excel files - alternative method
"""

import os
import sys
from pathlib import Path
import zipfile
from io import BytesIO

def extract_images_from_excel_zip(excel_path: Path, output_dir: Path):
    """Extract images by unzipping the xlsx file"""
    print(f"\nProcessing: {excel_path.name}")

    image_count = 0
    with zipfile.ZipFile(excel_path, 'r') as zf:
        # Find all images in the xl/media folder
        for info in zf.infolist():
            if info.filename.startswith('xl/media/'):
                # Get image extension
                ext = info.filename.split('.')[-1]
                # Create output filename
                sheet_name = 'unknown'
                # Try to find which drawing this belongs to
                base_name = f"{excel_path.stem}_{image_count+1:03d}"
                output_path = output_dir / f"{base_name}.{ext}"

                # Save the image
                with zf.open(info) as source, open(output_path, 'wb') as f:
                    f.write(source.read())

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
        count = extract_images_from_excel_zip(excel_file, output_dir)
        total_images += count

    print(f"\n=== Complete ===")
    print(f"Total {total_images} images extracted to: {output_dir}")

if __name__ == "__main__":
    main()
