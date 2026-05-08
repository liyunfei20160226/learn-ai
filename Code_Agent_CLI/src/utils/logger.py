"""
统一日志管理器

职责：
1. 初始化 Python logging 系统
2. 控制日志级别（通过环境变量）
3. 按日期自动切割日志文件
4. 提供简洁的静态方法：debug/info/warning/error
"""
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


class Logger:
    """统一日志管理器"""

    _initialized = False
    _logger: logging.Logger = None

    @classmethod
    def init(
        cls,
        log_dir: str = "logs",
        level: str = "INFO",
        log_file_prefix: str = "code-agent",
    ) -> None:
        """初始化日志系统（程序启动时调用一次）

        Args:
            log_dir: 日志目录，默认 logs/
            level: 日志级别：DEBUG/INFO/WARNING/ERROR，可通过 LOG_LEVEL 环境变量覆盖
            log_file_prefix: 日志文件前缀，默认 code-agent
        """
        if cls._initialized:
            return

        # 确保日志目录存在
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 创建 logger
        cls._logger = logging.getLogger("code-agent")
        level_name = level.upper()
        log_level = getattr(logging, level_name, logging.INFO)
        cls._logger.setLevel(log_level)
        cls._logger.propagate = False

        # 避免重复添加 handler
        if cls._logger.handlers:
            cls._initialized = True
            return

        # 文件 Handler：按日期切割，保留 30 天
        log_file = log_path / f"{log_file_prefix}.log"
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)-7s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        file_handler.setLevel(log_level)
        cls._logger.addHandler(file_handler)

        cls._initialized = True

    @classmethod
    def debug(cls, message: str, *args, **kwargs) -> None:
        """调试级别：详细信息，排查问题用"""
        if cls._logger:
            cls._logger.debug(message, *args, **kwargs)

    @classmethod
    def info(cls, message: str, *args, **kwargs) -> None:
        """信息级别：正常运行信息"""
        if cls._logger:
            cls._logger.info(message, *args, **kwargs)

    @classmethod
    def warning(cls, message: str, *args, **kwargs) -> None:
        """警告级别：有问题但不影响运行"""
        if cls._logger:
            cls._logger.warning(message, *args, **kwargs)

    @classmethod
    def error(cls, message: str, *args, **kwargs) -> None:
        """错误级别：功能异常，需要关注"""
        if cls._logger:
            cls._logger.error(message, *args, **kwargs)

    @classmethod
    def exception(cls, message: str, *args, **kwargs) -> None:
        """记录异常（包含堆栈）"""
        if cls._logger:
            cls._logger.exception(message, *args, **kwargs)
