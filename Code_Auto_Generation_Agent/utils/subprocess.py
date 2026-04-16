"""子进程执行封装"""

import subprocess
from typing import Tuple, Optional
from .logger import get_logger


logger = get_logger()


def run_command(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True
) -> Tuple[int, str, str]:
    """
    运行命令，返回退出码、stdout、stderr
    """
    logger.info(f"Running command: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True
        )
        return (
            result.returncode,
            result.stdout if capture_output else "",
            result.stderr if capture_output else ""
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {cmd}")
        return (-1, "", f"Timeout after {timeout} seconds")
    except Exception as e:
        logger.error(f"Command failed: {cmd}, error: {str(e)}")
        return (-1, "", str(e))


def check_command_available(cmd: str) -> bool:
    """检查命令是否可用"""
    try:
        returncode, _, _ = run_command(f"which {cmd}")
        return returncode == 0
    except Exception:
        return False
