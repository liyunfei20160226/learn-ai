"""配置管理 - 从环境变量加载配置"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    """应用配置"""
    ai_backend: str  # 'claude' or 'openai'
    claude_cmd: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_max_tokens: int
    max_retries: int
    max_validation_attempts: int
    output_base_dir: str


def get_config() -> Config:
    """从环境变量加载配置"""
    load_dotenv()

    ai_backend = os.getenv("DEFAULT_TOOL", "claude")
    claude_cmd = os.getenv("CLAUDE_CMD", "claude")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")

    try:
        openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "245760"))
    except ValueError:
        openai_max_tokens = 245760

    try:
        max_retries = int(os.getenv("MAX_RETRIES", "2"))
    except ValueError:
        max_retries = 2

    try:
        max_validation_attempts = int(os.getenv("MAX_VALIDATION_ATTEMPTS", "1"))
    except ValueError:
        max_validation_attempts = 1

    output_base_dir = os.getenv("OUTPUT_BASE_DIR", "./output")

    return Config(
        ai_backend=ai_backend,
        claude_cmd=claude_cmd,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        openai_max_tokens=openai_max_tokens,
        max_retries=max_retries,
        max_validation_attempts=max_validation_attempts,
        output_base_dir=output_base_dir,
    )
