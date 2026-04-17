"""Claude CLI 后端实现"""

import os
import tempfile
from typing import List

from core.ai_backend import AIBackend
from utils.logger import get_logger
from utils.subprocess import check_command_available, run_command

logger = get_logger()


class ClaudeCLIBackend(AIBackend):
    """Claude Code CLI 后端"""

    def __init__(self, claude_cmd: str = "claude", working_dir: str = None):
        self.claude_cmd = claude_cmd
        self.working_dir = working_dir

    def is_available(self) -> bool:
        """检查claude命令是否可用"""
        available = check_command_available(self.claude_cmd)
        if not available:
            logger.error(f"Claude CLI 不可用: {self.claude_cmd} 在PATH中找不到")
        return available

    def implement_story(self, prompt: str, write_files: bool = True) -> str:
        """实现用户故事 - 写入临时文件并调用claude
        write_files参数兼容接口，Claude CLI不直接写入文件，由外部处理
        """
        # 将prompt写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file = f.name

        try:
            cwd = self.working_dir or os.getcwd()
            cmd = f"{self.claude_cmd} --print {temp_file}"

            logger.info(f"调用 Claude CLI: {cmd}")
            returncode, stdout, stderr = run_command(cmd, cwd=cwd, timeout=3600)

            if returncode != 0:
                logger.error(f"Claude CLI 失败: 退出码={returncode}, 错误={stderr}")
                raise RuntimeError(f"Claude CLI 失败: {stderr}")

            logger.info("Claude CLI 执行成功完成")
            return stdout

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except Exception:
                pass

    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """修复错误"""
        from prompts import get_fix_errors_prompt
        template = get_fix_errors_prompt()
        error_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"""{original_prompt}

{template}

{error_text}

请修复这些错误。保持相同的输出格式。
"""
        return self.implement_story(prompt)
