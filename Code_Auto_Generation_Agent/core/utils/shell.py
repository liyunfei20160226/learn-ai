"""Shell 命令执行工具 - 统一封装 subprocess 调用"""

import logging
import shlex
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_shell_command(
    cmd: str,
    cwd: str | Path,
    shell: bool = False,
    timeout: int = 120,
    capture_output: bool = True,
) -> tuple[bool, str]:
    """安全执行 shell 命令

    统一处理：
    - 命令解析（shlex split）
    - 超时处理
    - 异常捕获
    - 输出编码

    Args:
        cmd: 要执行的命令字符串
        cwd: 工作目录
        shell: 是否使用 shell 模式（管道/重定向时需要）
        timeout: 超时时间（秒）
        capture_output: 是否捕获 stdout/stderr

    Returns:
        (是否成功, 输出内容)
    """
    try:
        # 包含管道/重定向时自动使用 shell 模式
        if not shell and ("|" in cmd or ">" in cmd or "<" in cmd or "&&" in cmd or "||" in cmd):
            shell = True

        if shell:
            cmd_list = cmd  # type: ignore
        else:
            cmd_list = shlex.split(cmd)

        result = subprocess.run(
            cmd_list,  # type: ignore
            cwd=str(cwd),
            shell=shell,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output

    except subprocess.TimeoutExpired as e:
        partial_output = str(e.stdout or "") + str(e.stderr or "")
        if partial_output:
            return False, f"命令执行超时（超过 {timeout} 秒）\n部分输出:\n{partial_output}"
        return False, f"命令执行超时（超过 {timeout} 秒）"

    except FileNotFoundError:
        return False, f"命令不存在或无法执行: {cmd.split()[0] if cmd.split() else 'empty'}"

    except PermissionError:
        return False, "权限不足，无法执行命令"

    except Exception as e:
        logger.exception(f"执行命令失败: {cmd[:100]}")
        return False, f"执行命令时发生异常: {type(e).__name__}: {e}"
