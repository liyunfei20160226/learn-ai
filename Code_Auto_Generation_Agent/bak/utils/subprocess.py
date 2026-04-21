"""子进程执行封装"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from config import COMMAND_WRAPPERS

from .logger import get_logger

logger = get_logger()


def _auto_wrap_command(cmd: str, cwd: Optional[str]) -> str:
    """
    自动检测项目类型，给命令加上正确的执行前缀

    解决的问题：
    - Python: pytest/ruff/mypy 被安装在虚拟环境中，直接运行会找不到命令
    - Node.js: eslint/tsc 被安装在 node_modules 中，需要 npx/pnpm exec

    配置来源：config.COMMAND_WRAPPERS
    """
    if not cmd.strip():
        return cmd

    # 已经有包装前缀了，跳过
    for wrapper in COMMAND_WRAPPERS:
        if cmd.startswith(wrapper["wrap_prefix"]):
            return cmd

    # 解析命令的第一个词
    cmd_parts = cmd.strip().split()
    if not cmd_parts:
        return cmd
    cmd_first = cmd_parts[0]

    base_dir = Path(cwd) if cwd else Path.cwd()

    # 依次匹配包装器
    for wrapper in COMMAND_WRAPPERS:
        # 检查命令是否在支持的列表中
        if cmd_first not in wrapper["commands"]:
            continue

        # 检查所有检测文件是否存在
        detect_files = wrapper["detect_files"]
        all_exist = all((base_dir / f).exists() for f in detect_files)

        if all_exist:
            wrapped_cmd = f"{wrapper['wrap_prefix']}{cmd}"
            logger.debug(f"[{wrapper['name']}自动包装] {cmd} → {wrapped_cmd}")
            return wrapped_cmd

    return cmd


def run_command(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    capture_output: bool = True,
    passthrough: bool = False,
) -> Tuple[int, str, str]:
    """
    运行命令，返回退出码、stdout、stderr

    特性：
    - 自动检测项目类型（uv/poetry/npm/pnpm），给命令加上正确的执行前缀
    - Windows 编码自动处理，避免乱码
    - passthrough 模式：不捕获输出，直接显示到控制台（避免 Windows 编码异常）

    Args:
        passthrough: 如果为 True，不捕获输出，直接透传到控制台。
                     适用于 npx/npm 等输出特殊字符的命令，避免 Windows cp932 编码异常。
    """
    # 自动包装命令
    original_cmd = cmd
    cmd = _auto_wrap_command(cmd, cwd)
    if cmd != original_cmd:
        logger.info(f"[自动包装] {original_cmd} → {cmd}")

    logger.info(f"运行命令: {cmd}")

    try:
        # 设置环境变量强制 UTF-8 编码，避免 Windows cp932 编码问题
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        if passthrough:
            # 透传模式：不捕获输出，直接显示到控制台
            # 彻底避免 Windows cp932 编码解码异常问题
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                stdout=sys.stdout,
                stderr=sys.stderr,
                env=env,
            )
            return (result.returncode, "", "")
        elif capture_output:
            # 手动以二进制方式读取，避免内部线程的编码问题
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            # 手动解码，使用 errors='replace' 避免 UnicodeDecodeError
            stdout = result.stdout.decode('utf-8', errors='replace')
            stderr = result.stderr.decode('utf-8', errors='replace')
            return (result.returncode, stdout, stderr)
        else:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                env=env
            )
            return (result.returncode, "", "")
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
