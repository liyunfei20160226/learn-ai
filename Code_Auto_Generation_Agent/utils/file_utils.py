"""文件操作工具"""

import json
import os
from typing import Any, Optional

from .logger import get_logger

logger = get_logger()


def ensure_dir(path: str) -> None:
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Created directory: {path}")


def read_json(path: str) -> Optional[Any]:
    """读取JSON文件"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"从 {path} 读取JSON失败: {str(e)}")
        return None


def write_json(path: str, data: Any) -> bool:
    """写入JSON文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"写入JSON到 {path} 失败: {str(e)}")
        return False


def read_file(path: str) -> Optional[str]:
    """读取文本文件"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件 {path} 失败: {str(e)}")
        return None


def write_file(path: str, content: str) -> bool:
    """写入文本文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件 {path} 失败: {str(e)}")
        return False
