"""Configuration management module.

Supports environment variable loading, type-safe validation, and default value management.
"""

from pathlib import Path
from typing import Optional

from pydantic import BeforeValidator, Field
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
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_base_url: OptionalStr = Field(None, description="OpenAI API Base URL")
    openai_model: str = Field("gpt-4o", description="Default model name")
    openai_timeout: int = Field(120, description="API timeout in seconds")
    openai_max_retries: int = Field(3, description="Maximum API retry count")
    openai_max_tokens: OptionalInt = Field(None, description="Maximum tokens per request")
    openai_temperature: float = Field(0.0, description="Sampling temperature (0.0 = deterministic)")

    # Agent execution configuration
    max_iterations: int = Field(50, description="Maximum agent iterations")

    # System configuration
    working_dir: str = Field("./output", description="Working directory")
    prompts_dir: str = Field("./prompts", description="Prompt templates directory")
    log_level: str = Field("INFO", description="Logging level")

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "AgentConfig":
        """Load configuration.

        Args:
            env_file: Optional path to environment file

        Returns:
            AgentConfig instance
        """
        if env_file and Path(env_file).exists():
            return cls(_env_file=env_file)
        return cls()


# Global configuration singleton
_global_config: Optional[AgentConfig] = None


def get_config(env_file: Optional[str] = None, reload: bool = False) -> AgentConfig:
    """Get global configuration singleton.

    Args:
        env_file: Optional path to environment file
        reload: Force reload configuration

    Returns:
        AgentConfig instance
    """
    global _global_config
    if _global_config is None or reload:
        _global_config = AgentConfig.load(env_file)
    return _global_config


def set_config(config: AgentConfig) -> None:
    """Set global configuration manually (for testing or dynamic config).

    Args:
        config: Configuration instance
    """
    global _global_config
    _global_config = config
