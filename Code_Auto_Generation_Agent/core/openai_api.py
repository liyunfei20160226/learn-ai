"""OpenAI API 后端实现"""

import os
import re
from typing import List
import openai
from core.ai_backend import AIBackend
from utils.logger import get_logger
from utils.file_utils import write_file, ensure_dir


logger = get_logger()


class OpenAIBackend(AIBackend):
    """OpenAI API 后端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        working_dir: str = None
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.working_dir = working_dir

        # 初始化客户端
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def is_available(self) -> bool:
        """检查配置是否完整"""
        if not self.api_key:
            logger.error("OpenAI API key 未提供")
            return False
        return True

    def implement_story(self, prompt: str) -> str:
        """实现用户故事 - 调用OpenAI API并写入文件"""
        logger.info(f"调用 OpenAI API 模型={self.model}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=16384
            )

            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("OpenAI 返回空响应")

            logger.info("OpenAI API 调用成功完成")

            # 解析AI输出，提取文件并写入磁盘
            self._write_files_from_output(content)

            return content

        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {str(e)}")
            raise RuntimeError(f"OpenAI API 失败: {str(e)}")

    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """修复错误"""
        error_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"""{original_prompt}

# 当前实现完成后，运行质量检查发现以下错误：

{error_text}

请修复这些错误。保持输出格式一致。
"""
        return self.implement_story(prompt)

    def _write_files_from_output(self, output: str) -> None:
        """从AI输出中解析文件并写入磁盘

        支持两种格式:
        1. --- full/path/to/file --- 后跟代码内容
        2. ```full/path/to/file 后跟代码内容
        """
        # 模式1: --- path ---
        # 模式2: ```path
        file_blocks = []

        # 查找 --- path --- 格式
        pattern1 = r'-{3,}\s*(.*?)\s*-{3,}\n(.*?)(?=\n-{3,}|\Z)'
        matches1 = re.finditer(pattern1, output, re.DOTALL)
        for match in matches1:
            path = match.group(1).strip()
            content = match.group(2)
            if path:
                file_blocks.append((path, content))

        # 查找 ```path 格式
        pattern2 = r'```(?:[^\n]*?)([^\n`]+)\n(.*?)\n```'
        matches2 = re.finditer(pattern2, output, re.DOTALL)
        for match in matches2:
            path = match.group(1).strip()
            content = match.group(2)
            if path:
                file_blocks.append((path, content))

        if not file_blocks:
            logger.warning("AI输出中没有找到文件块")
            return

        # 写入每个文件
        cwd = self.working_dir or os.getcwd()
        written = 0
        for rel_path, content in file_blocks:
            # 处理绝对路径，相对于工作目录
            if os.path.isabs(rel_path):
                full_path = rel_path
            else:
                full_path = os.path.join(cwd, rel_path)

            # 标准化路径
            full_path = os.path.normpath(full_path)

            if write_file(full_path, content):
                logger.info(f"已写入文件: {rel_path}")
                written += 1
            else:
                logger.error(f"写入文件失败: {rel_path}")

        logger.info(f"AI输出中共写入 {written} 个文件")
