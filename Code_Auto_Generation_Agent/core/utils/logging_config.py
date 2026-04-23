"""统一日志配置模块"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str = None, log_file: str | Path = None, level: int = logging.INFO) -> logging.Logger:
    """设置并返回一个配置好的 logger

    Args:
        name: logger 名称（None 表示 root logger）
        log_file: 日志文件路径（可选）
        level: 日志级别

    Returns:
        配置好的 Logger 对象
    """
    logger = logging.getLogger(name or __name__)
    logger.setLevel(level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 项目级别的通用 logger
_logger_initialized = False


def get_project_logger() -> logging.Logger:
    """获取项目通用 logger（单例模式）"""
    global _logger_initialized
    if not _logger_initialized:
        setup_logger("codegen", "codegen.log")
        _logger_initialized = True
    return logging.getLogger("codegen")
