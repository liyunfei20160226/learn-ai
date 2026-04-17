"""OpenAI API 后端实现"""

import os
import re
from typing import List

import openai

from core.ai_backend import AIBackend
from utils.file_utils import write_file
from utils.logger import get_logger

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

    def implement_story(self, prompt: str, write_files: bool = True) -> str:
        """实现用户故事 - 调用OpenAI API
        如果write_files=True，解析代码块并写入文件
        """
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

            # 如果需要，解析AI输出，提取文件并写入磁盘
            if write_files:
                self._write_files_from_output(content)

            return content

        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {str(e)}")
            raise RuntimeError(f"OpenAI API 失败: {str(e)}")

    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """修复错误"""
        from prompts import get_fix_errors_prompt
        template = get_fix_errors_prompt()
        error_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"""{original_prompt}

{template}

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
        # 支持多种情况：
        # 1. ```filepath\ncontent``` (路径在第一行)
        # 2. ```language\nfilepath\ncontent``` (路径在第二行，第一行是语言标记)
        # 3. ```\n### 标题说明\n...\nfilepath\ncontent``` (有markdown标题说明，需要跳过说明找路径)
        pattern2 = r'```([^\n`]*)\n(.*?)\n```'
        matches2 = re.finditer(pattern2, output, re.DOTALL)
        for match in matches2:
            first_line = match.group(1).strip()
            rest = match.group(2)

            path = None
            content = None

            # 检查第一行是否看起来像文件路径（包含斜杠或点，且不是markdown标题）
            if ('/' in first_line or '.' in first_line) and not first_line.startswith('#') and '`' not in first_line:
                # 第一行就是路径
                path = first_line
                content = rest
            else:
                # 第一行不是路径，需要逐行找真正的路径
                lines = rest.split('\n')
                # 跳过markdown标题、说明等，找第一个看起来像路径的行
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    # 跳过空行、markdown标题、反引号包裹的标题行
                    if (not line_stripped
                        or line_stripped.startswith('#')
                        or line_stripped.startswith('`')
                        or line_stripped.endswith('`')):
                        continue
                    # 检查这行是否看起来像文件路径
                    if '/' in line_stripped or '.' in line_stripped:
                        # 找到路径了，后面都是内容
                        path = line_stripped
                        content = '\n'.join(lines[i+1:])
                        break
                # 如果没找到，第一行是语言标记，第二行试一下
                if path is None and len(lines) >= 2:
                    second_line = lines[0].strip()
                    if second_line:
                        path = second_line
                        content = '\n'.join(lines[1:])
                if path is None:
                    # 还是找不到，跳过
                    continue
            if path:
                # 清理路径：移除反引号
                path = path.replace('`', '').strip()
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
