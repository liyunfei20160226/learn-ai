"""文件工具"""
import json
import os
from typing import Any, Optional

from utils.logger import get_logger

logger = get_logger()


def ensure_dir(path: str) -> None:
    """确保目录存在，不存在则创建"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"创建目录: {path}")


def read_json(path: str) -> Optional[Any]:
    """读取JSON文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取JSON文件失败 {path}: {e}")
        return None


def write_json(path: str, data: Any) -> bool:
    """写入JSON文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"写入JSON文件: {path}")
        return True
    except Exception as e:
        logger.error(f"写入JSON文件失败 {path}: {e}")
        return False


def read_text(path: str) -> Optional[str]:
    """读取文本文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文本文件失败 {path}: {e}")
        return None


def write_text(path: str, content: str) -> bool:
    """写入文本文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文本文件失败 {path}: {e}")
        return False
