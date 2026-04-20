"""Claude CLI 后端实现"""
import os
import tempfile
from typing import Optional

from core.ai_backend import AIBackend
from utils.logger import get_logger
from utils.subprocess import run_command

logger = get_logger()


class ClaudeCLIBackend(AIBackend):
    """Claude Code CLI 后端"""

    def __init__(self, claude_cmd: str = "claude", working_dir: str = "."):
        self.claude_cmd = claude_cmd
        self.working_dir = working_dir

    def is_available(self) -> bool:
        """检查claude命令是否可用"""
        code, _, _ = run_command(f"{self.claude_cmd} --version")
        return code == 0

    def generate(self, prompt: str) -> Optional[str]:
        """调用claude生成内容

        Claude CLI 需要从文件输入prompt，因为prompt可能很大。
        """
        # 将prompt写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            temp_file = f.name

        try:
            # 调用claude
            # --print 选项让claude直接输出结果到stdout
            cmd = f"{self.claude_cmd} --print {temp_file}"
            code, stdout, stderr = run_command(cmd, cwd=self.working_dir, timeout=600)

            if code != 0:
                logger.error(f"Claude CLI 调用失败: code={code}, stderr={stderr}")
                return None

            logger.info(f"Claude CLI 调用成功，输出长度: {len(stdout)}")
            return stdout

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except Exception:
                pass
