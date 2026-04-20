"""子进程工具 - 封装调用外部命令"""
import subprocess
from typing import Optional, Tuple

from utils.logger import get_logger

logger = get_logger()


def run_command(
    cmd: str,
    cwd: Optional[str] = None,
    capture_output: bool = True,
    timeout: Optional[int] = None
) -> Tuple[int, str, str]:
    """运行外部命令，返回退出码、stdout、stderr"""
    logger.info(f"运行命令: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        return (
            result.returncode,
            result.stdout if capture_output else "",
            result.stderr if capture_output else ""
        )
    except subprocess.TimeoutExpired:
        logger.error(f"命令超时: {cmd}")
        return (1, "", f"Timeout after {timeout} seconds")
    except Exception as e:
        logger.error(f"命令执行失败: {cmd}, error: {e}")
        return (1, "", str(e))
