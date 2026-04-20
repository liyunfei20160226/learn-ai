"""OpenAI API 后端实现"""
from typing import Optional

from openai import APIConnectionError, APIError, OpenAI

from core.ai_backend import AIBackend
from utils.logger import get_logger

logger = get_logger()


class OpenAIBackend(AIBackend):
    """OpenAI API 后端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        max_tokens: int = 245760,
        working_dir: str = "."
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.working_dir = working_dir
        self._client: Optional[OpenAI] = None

    def _init_client(self) -> bool:
        """初始化OpenAI客户端"""
        if self._client is not None:
            return True

        if not self.api_key:
            logger.error("OpenAI API key 未配置")
            return False

        try:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            return True
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {e}")
            return False

    def is_available(self) -> bool:
        """检查是否可用"""
        return self._init_client()

    def generate(self, prompt: str) -> Optional[str]:
        """调用OpenAI API生成内容"""
        if not self._init_client():
            return None

        try:
            logger.info(f"调用OpenAI API，模型: {self.model}，prompt长度: {len(prompt)}")

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            if content is None:
                logger.error("OpenAI 返回空内容")
                return None

            logger.info(f"OpenAI API 调用成功，输出长度: {len(content)}")
            return content

        except APIConnectionError as e:
            logger.error(f"OpenAI API 连接错误: {e}")
            return None
        except APIError as e:
            logger.error(f"OpenAI API 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            return None
