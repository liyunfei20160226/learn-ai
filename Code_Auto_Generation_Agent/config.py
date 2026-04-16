"""配置管理模块"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """应用配置"""
    # AI后端配置
    ai_backend: str = "claude"  # "claude" 或 "openai"

    # Claude CLI配置
    claude_cmd: str = "claude"

    # OpenAI API配置
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # 质量检查命令
    quality_check_cmd: Optional[str] = "ruff check ."
    type_check_cmd: Optional[str] = None
    test_cmd: Optional[str] = "pytest"

    # 重试配置
    max_retries: int = 3
    max_fix_attempts: int = 3

    # Git配置
    git_auto_commit: bool = True

    # 输出配置
    output_base_dir: str = "./output"


def load_config() -> Config:
    """从环境变量加载配置"""
    load_dotenv()

    config = Config()

    # 默认AI工具
    if os.getenv("DEFAULT_TOOL"):
        config.ai_backend = os.getenv("DEFAULT_TOOL").strip()

    # Claude CLI
    if os.getenv("CLAUDE_CMD"):
        config.claude_cmd = os.getenv("CLAUDE_CMD").strip()

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        config.openai_api_key = os.getenv("OPENAI_API_KEY").strip()
    if os.getenv("OPENAI_BASE_URL"):
        config.openai_base_url = os.getenv("OPENAI_BASE_URL").strip()
    if os.getenv("OPENAI_MODEL"):
        config.openai_model = os.getenv("OPENAI_MODEL").strip()

    # 质量检查
    if os.getenv("QUALITY_CHECK_CMD") is not None:
        config.quality_check_cmd = os.getenv("QUALITY_CHECK_CMD").strip() or None
    if os.getenv("TYPE_CHECK_CMD") is not None:
        config.type_check_cmd = os.getenv("TYPE_CHECK_CMD").strip() or None
    if os.getenv("TEST_CMD") is not None:
        config.test_cmd = os.getenv("TEST_CMD").strip() or None

    # 重试配置
    if os.getenv("MAX_RETRIES"):
        config.max_retries = int(os.getenv("MAX_RETRIES"))
    if os.getenv("MAX_FIX_ATTEMPTS"):
        config.max_fix_attempts = int(os.getenv("MAX_FIX_ATTEMPTS"))

    # Git
    if os.getenv("GIT_AUTO_COMMIT") is not None:
        config.git_auto_commit = os.getenv("GIT_AUTO_COMMIT").lower() in ("true", "1", "yes")

    # 输出
    if os.getenv("OUTPUT_BASE_DIR"):
        config.output_base_dir = os.getenv("OUTPUT_BASE_DIR").strip()

    return config


def get_config() -> Config:
    """获取配置"""
    return load_config()
