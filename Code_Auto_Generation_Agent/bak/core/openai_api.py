"""OpenAI API 后端实现 - 使用 LangChain"""

import os
import re
from typing import List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

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
        working_dir: str = None,
        max_tokens: int = 32768,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.working_dir = working_dir
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        # 初始化 LangChain ChatOpenAI，内置重试机制
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            max_tokens=max_tokens,
            max_retries=max_retries,  # LangChain 内置重试机制
            timeout=600,  # 10分钟超时
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
        如果AI输出格式不正确，会自动要求重试一次
        """
        logger.info(f"调用 OpenAI API (LangChain) 模型={self.model}")

        try:
            # LangChain 内置重试机制
            response = self.llm.invoke([HumanMessage(content=prompt)])

            content = response.content
            if not content:
                raise RuntimeError("OpenAI 返回空响应")

            logger.info(f"OpenAI API 调用成功完成，输出长度: {len(content)} 字符")

            # 如果需要，解析AI输出，提取文件并写入磁盘
            if write_files:
                success = self._write_files_from_output(content)
                # 如果没有找到有效文件，让AI重试一次
                if not success:
                    logger.warning("AI输出格式不正确，要求重新生成...")
                    retry_prompt = prompt + """

⚠️ 重要提醒：你的上一次输出格式不正确！
代码块的第一行必须是完整的文件相对路径，不要加任何语言标记！

❌ 错误示例：
```python
backend/app/main.py
内容...
```

✅ 正确示例（第一行必须是路径）：
```backend/app/main.py
内容...
```

请严格按照正确格式重新输出你的答案。
"""
                    logger.info("正在调用AI重新生成...")
                    retry_response = self.llm.invoke([HumanMessage(content=retry_prompt)])
                    content = retry_response.content
                    logger.info(f"AI重试完成，输出长度: {len(content)} 字符")
                    self._write_files_from_output(content)

            return content

        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {str(e)}")
            raise RuntimeError(f"OpenAI API 失败: {str(e)}")

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
                            logger.info(f"提取错误相关文件: {path}")
                        except Exception as e:
                            logger.debug(f"读取文件失败 {path}: {e}")

        if not content_parts:
            return "（未能从错误信息中提取相关文件）"

        return "\n".join(content_parts)

    def _write_files_from_output(self, output: str) -> bool:
        """从AI输出中解析文件并写入磁盘

        返回是否成功找到并写入至少一个文件
        如果失败，可以让AI重试
        """
        file_blocks = []

        # 正则：```[第一行内容]\n[剩余内容]```
        pattern = r'```([^\n`]*)\n(.*?)```'
        matches = list(re.finditer(pattern, output, re.DOTALL))

        logger.info(f"找到 {len(matches)} 个代码块")

        for idx, match in enumerate(matches):
            first_line = match.group(1).strip()
            rest = match.group(2)

            # 情况1：第一行就是路径
            path = None
            content = None
            if self._is_likely_file_path(first_line):
                path = first_line
                content = rest
                logger.info(f"代码块 {idx}: 第一行是路径 '{path}'")
            else:
                # 情况2：第一行是语言标记，检查内容的第一行是否是路径
                lines = rest.split('\n', 2)
                if len(lines) >= 1 and self._is_likely_file_path(lines[0]):
                    path = lines[0]
                    content = '\n'.join(lines[1:]) if len(lines) > 1 else ''
                    logger.info(f"代码块 {idx}: 内容第一行是路径 '{path}'")
                elif len(lines) >= 2 and self._is_likely_file_path(lines[1]):
                    path = lines[1]
                    content = '\n'.join(lines[2:]) if len(lines) > 2 else ''
                    logger.info(f"代码块 {idx}: 内容第二行是路径 '{path}'")

            if not path:
                logger.warning(f"代码块 {idx}: 未找到有效路径")
                continue

            # 路径有效性检查
            if path == '.' or len(path) > 200:
                logger.warning(f"代码块 {idx}: 跳过无效路径 '{path}'")
                continue

            # 跳过URL
            if 'http://' in path or 'https://' in path:
                logger.warning(f"代码块 {idx}: 跳过URL '{path}'")
                continue

            file_blocks.append((path, content))
            logger.info(f"代码块 {idx}: ✓ {path}")

        if not file_blocks:
            logger.warning("没有找到有效文件")
            return False

        # 写入文件
        cwd = self.working_dir or os.getcwd()
        written = 0
        for rel_path, content in file_blocks:
            if os.path.isabs(rel_path):
                full_path = rel_path
            else:
                full_path = os.path.join(cwd, rel_path)
            full_path = os.path.normpath(full_path)

            if write_file(full_path, content):
                logger.info(f"已写入: {rel_path}")
                written += 1
            else:
                logger.error(f"写入失败: {rel_path}")

        logger.info(f"共写入 {written} 个文件")
        return written > 0

    def _is_likely_file_path(self, s: str) -> bool:
        """判断字符串是否看起来像文件路径"""
        s = s.strip()
        if not s:
            return False
        # 必须包含 / 或 . （路径或文件扩展名）
        if '/' not in s and '.' not in s:
            return False
        # 不能是纯语言标记
        if s.lower() in ['python', 'py', 'javascript', 'js', 'typescript', 'ts',
                         'json', 'yaml', 'yml', 'html', 'css', 'bash', 'shell']:
            return False
        # 不能是特殊标记
        if s.startswith('#') or s.startswith('`'):
            return False
        return True
