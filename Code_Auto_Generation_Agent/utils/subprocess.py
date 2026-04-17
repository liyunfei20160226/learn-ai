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
    logger.info(f"运行命令: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return (
            result.returncode,
            result.stdout if capture_output else "",
            result.stderr if capture_output else ""
        )
    except subprocess.TimeoutExpired:
        logger.error(f"命令超时: {cmd}")
        return (-1, "", f"超时 {timeout} 秒")
    except Exception as e:
        logger.error(f"命令执行失败: {cmd}, 错误: {str(e)}")
        return (-1, "", str(e))


def check_command_available(cmd: str) -> bool:
    """检查命令是否可用"""
    try:
        returncode, _, _ = run_command(f"which {cmd}")
        return returncode == 0
    except Exception:
        return False
