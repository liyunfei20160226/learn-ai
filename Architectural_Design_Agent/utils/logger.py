"""日志工具"""
import logging
import os
from datetime import datetime
from typing import Optional

# 全局日志实例
_logger_instance: Optional[logging.Logger] = None


def setup_logger(name: str = "auto_design") -> logging.Logger:
    """设置日志，输出到控制台和文件"""
    global _logger_instance

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件handler
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"auto_design_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    _logger_instance = logger
    return logger


def get_logger() -> logging.Logger:
    """获取全局日志实例"""
    global _logger_instance
    if _logger_instance is None:
        return setup_logger()
    return _logger_instance
