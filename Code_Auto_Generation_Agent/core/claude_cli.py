"""Claude CLI 后端实现"""

import os
import tempfile
from typing import List
from core.ai_backend import AIBackend
from utils.subprocess import run_command, check_command_available
from utils.logger import get_logger
from utils.file_utils import read_file


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
            logger.error(f"Claude CLI not available: {self.claude_cmd} not found in PATH")
        return available

    def implement_story(self, prompt: str) -> str:
        """实现用户故事 - 写入临时文件并调用claude"""
        # 将prompt写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file = f.name

        try:
            cwd = self.working_dir or os.getcwd()
            cmd = f"{self.claude_cmd} --print {temp_file}"

            logger.info(f"Calling Claude CLI: {cmd}")
            returncode, stdout, stderr = run_command(cmd, cwd=cwd, timeout=3600)

            if returncode != 0:
                logger.error(f"Claude CLI failed: returncode={returncode}, stderr={stderr}")
                raise RuntimeError(f"Claude CLI failed: {stderr}")

            logger.info("Claude CLI completed successfully")
            return stdout

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass

    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """修复错误"""
        error_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"""{original_prompt}

# 当前实现完成后，运行质量检查发现以下错误：

{error_text}

请修复这些错误。保持相同的输出格式。
"""
        return self.implement_story(prompt)
