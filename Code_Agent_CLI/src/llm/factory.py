"""
LLM Provider 工厂函数

根据 .env 配置自动创建对应的 LLM Provider。
设计模式：工厂模式。

使用方法：
    from llm.factory import get_llm_provider
    llm = get_llm_provider()  # 自动从环境变量读取配置
"""
import os
from .base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """
    根据 LLM_PROVIDER 环境变量创建对应的 Provider 实例

    支持的提供商：
        - claude: Anthropic Claude
        - openai: OpenAI 兼容格式
        - ollama: 本地模型（需要先安装 Ollama 并下载模型）

    Returns:
        LLMProvider 实例

    Raises:
        ValueError: 如果提供商不支持，或者配置错误
    """
    provider = os.getenv("LLM_PROVIDER", "claude").lower()

    if provider == "claude":
        from .claude_provider import ClaudeProvider
        return ClaudeProvider()

    elif provider == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()

    elif provider == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider()

    else:
        raise ValueError(
            f"不支持的 LLM Provider: {provider}\n"
            f"支持的选项：claude, openai, ollama"
        )
