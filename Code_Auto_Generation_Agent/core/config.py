"""Configuration management module.

Supports environment variable loading, type-safe validation, and default value management.
"""

import threading
from pathlib import Path
from typing import Optional

from pydantic import BeforeValidator, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def empty_str_to_none(v: str) -> Optional[str]:
    """Convert empty string to None."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


OptionalStr = Annotated[Optional[str], BeforeValidator(empty_str_to_none)]
OptionalInt = Annotated[Optional[int], BeforeValidator(empty_str_to_none)]


class AgentConfig(BaseSettings):
    """Global agent configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI API configuration
    openai_api_key: OptionalStr = Field(None, description="OpenAI API Key")
    openai_base_url: OptionalStr = Field(None, description="OpenAI API Base URL")
    openai_model: str = Field("gpt-4o", description="Default model name")
    openai_timeout: int = Field(600, description="API timeout in seconds")
    openai_max_retries: int = Field(3, description="Maximum API retry count")
    openai_max_tokens: OptionalInt = Field(None, description="Maximum tokens per request")
    openai_temperature: float = Field(0.0, description="Sampling temperature (0.0 = deterministic)")

    # Agent execution configuration
    max_iterations: int = Field(50, description="Maximum agent iterations")
    max_fix_attempts: int = Field(20, description="Maximum auto-fix attempts before giving up")

    # System configuration
    working_dir: str = Field("./output", description="Working directory")
    prompts_dir: str = Field("./prompts", description="Prompt templates directory")
    log_level: str = Field("INFO", description="Logging level")

    @field_validator("openai_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v

    @field_validator("openai_max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"Max retries must be non-negative, got {v}")
        return v

    @field_validator("openai_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"Timeout must be positive, got {v}")
        return v

    @field_validator("max_iterations", "max_fix_attempts")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"Value must be positive, got {v}")
        return v

    # ========== 常量配置（集中管理所有魔法数字）==========

    # 工具调用配置
    DEFAULT_TOOL_COUNT: int = 5
    ERROR_SAMPLE_COUNT: int = 5

    # 快照管理配置
    SNAPSHOT_BATCH_SIZE: int = 1000

    # 质量检查配置
    LINT_CHECK_TIMEOUT: int = 120
    TYPE_CHECK_TIMEOUT: int = 180
    QUALITY_CHECK_TIMEOUT: int = 300

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "AgentConfig":
        """Load configuration.

        Args:
            env_file: Optional path to environment file

        Returns:
            AgentConfig instance

        Raises:
            ValueError: If env_file is not a valid file or not readable
        """
        if env_file:
            env_path = Path(env_file)
            if env_path.is_dir():
                raise ValueError(f"env_file must be a file, not a directory: {env_file}")
            if not env_path.exists():
                raise ValueError(f"Configuration file not found: {env_file}")
            if not env_path.is_file():
                raise ValueError(f"{env_file} is not a valid file")
            return cls(_env_file=env_file)  # type: ignore[call-arg]
        return cls()


# Global configuration singleton
_global_config: Optional[AgentConfig] = None
_config_lock = threading.Lock()


def get_config(env_file: Optional[str] = None, reload: bool = False) -> AgentConfig:
    """Get global configuration singleton.

    Args:
        env_file: Optional path to environment file
        reload: Force reload configuration

    Returns:
        AgentConfig instance
    """
    global _global_config
    # Double-checked locking for thread safety
    if _global_config is None or reload:
        with _config_lock:
            if _global_config is None or reload:
                _global_config = AgentConfig.load(env_file)
    return _global_config


def set_config(config: AgentConfig) -> None:
    """Set global configuration manually (for testing or dynamic config).

    Args:
        config: Configuration instance
    """
    global _global_config
    with _config_lock:
        _global_config = config
