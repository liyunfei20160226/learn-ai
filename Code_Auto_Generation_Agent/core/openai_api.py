"""OpenAI API 后端实现"""

from typing import List
import openai
from core.ai_backend import AIBackend
from utils.logger import get_logger


logger = get_logger()


class OpenAIBackend(AIBackend):
    """OpenAI API 后端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

        # 初始化客户端
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def is_available(self) -> bool:
        """检查配置是否完整"""
        if not self.api_key:
            logger.error("OpenAI API key not provided")
            return False
        return True

    def implement_story(self, prompt: str) -> str:
        """实现用户故事 - 调用OpenAI API"""
        logger.info(f"Calling OpenAI API model={self.model}")

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
                raise RuntimeError("Empty response from OpenAI")

            logger.info("OpenAI API call completed successfully")
            return content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise RuntimeError(f"OpenAI API failed: {str(e)}")

    def fix_errors(self, original_prompt: str, errors: List[str]) -> str:
        """修复错误"""
        error_text = "\n".join(f"- {error}" for error in errors)
        prompt = f"""{original_prompt}

# 当前实现完成后，运行质量检查发现以下错误：

{error_text}

请修复这些错误。保持输出格式一致。
"""
        return self.implement_story(prompt)
