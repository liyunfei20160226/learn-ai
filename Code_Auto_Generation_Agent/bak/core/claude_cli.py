"""Claude CLI 后端实现"""

import os
import tempfile
from typing import List

from config import get_config
from core.ai_backend import AIBackend
from utils.logger import get_logger
from utils.subprocess import check_command_available, run_command

logger = get_logger()
config = get_config()


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
            returncode, stdout, stderr = run_command(cmd, cwd=cwd, timeout=config.timeout.ai_command)

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

    def fix_errors(self, original_prompt: str, errors: List[str], target_dir: str = None) -> str:
        """修复错误
        target_dir: 项目根目录，用于检测实际的配置文件和版本
        """
        from prompts import get_fix_errors_prompt
        template = get_fix_errors_prompt(target_dir)
        error_text = "\n".join(f"- {error}" for error in errors)

        # 从错误信息中提取文件路径并读取完整内容
        file_contents = self._extract_and_read_files_from_errors(errors, target_dir)

        prompt = template.replace("{{ORIGINAL_PROMPT}}", original_prompt)
        prompt = prompt.replace("{{ERROR_LIST}}", error_text)
        prompt = prompt.replace("{{FILE_CONTENTS}}", file_contents)

        return self.implement_story(prompt)

    def _extract_and_read_files_from_errors(self, errors: List[str], target_dir: str = None) -> str:
        """从错误信息中提取文件路径，读取文件完整内容
        这样 AI 就能基于完整文件进行修复，不会只返回片段
        """
        import os
        import re

        if not target_dir:
            target_dir = self.working_dir or os.getcwd()

        # 从错误信息中提取文件路径的正则
        # 支持格式：filepath:line:col, 或 filepath:line, 或 "filepath"
        path_pattern = r'([a-zA-Z0-9_\-\/\\\.]+\.[a-zA-Z0-9]+)'

        found_files = set()
        content_parts = []

        for error in errors:
            matches = re.findall(path_pattern, error)
            for path in matches:
                # 标准化路径
                if path.startswith('./') or path.startswith('.\\'):
                    path = path[2:]
                if path not in found_files:
                    found_files.add(path)
                    full_path = os.path.join(target_dir, path)
                    if os.path.exists(full_path):
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            content_parts.append(f"--- {path} ---\n{content}\n")
                        except Exception:
                            pass

        if not content_parts:
            return "（未能从错误信息中提取相关文件）"

        return "\n".join(content_parts)
