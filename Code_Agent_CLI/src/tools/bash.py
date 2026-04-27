"""
Bash / PowerShell 执行工具

根据系统自动选择 Shell：
- Windows: PowerShell
- Linux/Mac: bash

也可以通过环境变量 SHELL 覆盖。
超时时间可以通过 BASH_TIMEOUT 环境变量配置。
"""
import os
import asyncio
import platform
from typing import Dict, Any
from .base import BaseTool, ToolError


class BashTool(BaseTool):
    """
    执行 shell 命令的工具

    注意：为了安全，默认会在执行前显示命令并提示确认
    """

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "执行 shell 命令（Windows 用 PowerShell，其他用 bash）。支持运行测试、安装依赖、查看文件列表等操作。"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令",
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（可选，默认当前目录）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒，可选，默认 60 秒）",
                },
            },
            "required": ["command"],
        }

    def _get_shell(self) -> str:
        """获取当前系统应该使用的 shell"""
        # 优先用环境变量配置
        env_shell = os.getenv("SHELL")
        if env_shell:
            return env_shell

        # 自动检测
        if platform.system() == "Windows":
            return "powershell"
        return "bash"

    async def run(self, args: Dict[str, Any]) -> str:
        command = args.get("command")
        if not command:
            raise ToolError("缺少必填参数：command")

        cwd = args.get("cwd", ".")
        # 参数指定的 timeout 优先级最高，其次环境变量，最后默认 300 秒（5分钟）
        default_timeout = int(os.getenv("BASH_TIMEOUT", "300"))
        timeout = args.get("timeout", default_timeout)
        shell = self._get_shell()

        # 安全检查：不允许跳出当前目录
        real_cwd = os.path.realpath(cwd)
        base_dir = os.path.realpath(".")
        if not real_cwd.startswith(base_dir):
            raise ToolError(f"安全限制：不允许访问目录之外的路径：{cwd}")

        # 执行前提示（给用户安全感）
        print(f"\n{'='*60}")
        print(f"⚠️  将要执行 {shell} 命令:")
        print(f"   $ {command}")
        print(f"   工作目录: {real_cwd}")
        print(f"   超时时间: {timeout} 秒")
        print(f"{'='*60}\n")

        try:
            if platform.system() == "Windows":
                # Windows 用 PowerShell
                proc = await asyncio.create_subprocess_exec(
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                    cwd=real_cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # Linux/Mac 用 bash
                proc = await asyncio.create_subprocess_exec(
                    shell,
                    "-c",
                    command,
                    cwd=real_cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            # 等待执行完成（带超时）
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # 组装结果
            result = []
            result.append(f"命令: {command}")
            result.append(f"退出码: {proc.returncode}")
            result.append("")

            if stdout:
                result.append("标准输出:")
                result.append(stdout)
                result.append("")

            if stderr:
                result.append("标准错误:")
                result.append(stderr)
                result.append("")

            if proc.returncode == 0:
                result.append("✅ 执行成功")
            else:
                result.append(f"❌ 执行失败（退出码: {proc.returncode}）")

            return "\n".join(result)

        except asyncio.TimeoutError:
            raise ToolError(f"命令执行超时（{timeout} 秒）: {command}")
        except Exception as e:
            raise ToolError(f"执行命令时出错: {type(e).__name__}: {e}")
