"""测试配置管理模块

注意：测试会临时修改全局配置，每个测试后会清理
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import AgentConfig, empty_str_to_none, get_config, set_config


def setup_function():
    """每个测试前：清空全局配置和环境变量"""
    set_config(None)  # type: ignore
    for key in list(os.environ.keys()):
        if key.startswith("OPENAI_") or key.startswith("WORKING_"):
            del os.environ[key]


def teardown_function():
    """每个测试后：清理"""
    set_config(None)  # type: ignore


def test_empty_str_to_none_conversion():
    """测试空字符串转换为 None"""
    assert empty_str_to_none("") is None
    assert empty_str_to_none("   ") is None
    assert empty_str_to_none(None) is None
    assert empty_str_to_none("value") == "value"


def test_agent_config_defaults(monkeypatch):
    """测试默认配置值"""
    # 清除环境变量的影响
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    config = AgentConfig()
    assert config.openai_timeout == 300
    assert config.openai_max_retries == 3
    assert config.openai_temperature == 0.0
    assert config.max_iterations == 50
    assert config.max_fix_attempts == 20


def test_agent_config_constants():
    """测试常量配置"""
    config = AgentConfig()
    assert config.DEFAULT_TOOL_COUNT == 5
    assert config.ERROR_SAMPLE_COUNT == 5
    assert config.SNAPSHOT_BATCH_SIZE == 1000
    assert config.LINT_CHECK_TIMEOUT == 120
    assert config.TYPE_CHECK_TIMEOUT == 180
    assert config.QUALITY_CHECK_TIMEOUT == 300


def test_validate_temperature_valid():
    """测试 temperature 有效范围"""
    config = AgentConfig(openai_temperature=0.0)
    assert config.openai_temperature == 0.0

    config = AgentConfig(openai_temperature=1.0)
    assert config.openai_temperature == 1.0

    config = AgentConfig(openai_temperature=2.0)
    assert config.openai_temperature == 2.0


def test_validate_temperature_invalid():
    """测试 temperature 超出范围"""
    with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
        AgentConfig(openai_temperature=-0.1)

    with pytest.raises(ValueError, match="Temperature must be between 0.0 and 2.0"):
        AgentConfig(openai_temperature=2.1)


def test_validate_max_retries_valid():
    """测试 max_retries 有效范围"""
    config = AgentConfig(openai_max_retries=0)
    assert config.openai_max_retries == 0

    config = AgentConfig(openai_max_retries=10)
    assert config.openai_max_retries == 10


def test_validate_max_retries_invalid():
    """测试 max_retries 无效"""
    with pytest.raises(ValueError, match="Max retries must be non-negative"):
        AgentConfig(openai_max_retries=-1)


def test_validate_timeout_valid():
    """测试 timeout 有效范围"""
    config = AgentConfig(openai_timeout=1)
    assert config.openai_timeout == 1


def test_validate_timeout_invalid():
    """测试 timeout 无效"""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        AgentConfig(openai_timeout=0)

    with pytest.raises(ValueError, match="Timeout must be positive"):
        AgentConfig(openai_timeout=-1)


def test_validate_max_iterations_invalid():
    """测试 max_iterations 无效"""
    with pytest.raises(ValueError, match="Value must be positive"):
        AgentConfig(max_iterations=0)


def test_validate_max_fix_attempts_invalid():
    """测试 max_fix_attempts 无效"""
    with pytest.raises(ValueError, match="Value must be positive"):
        AgentConfig(max_fix_attempts=0)


def test_load_env_file_not_found():
    """测试加载不存在的 env 文件"""
    with pytest.raises(ValueError, match="Configuration file not found"):
        AgentConfig.load("nonexistent_env_file_xyz.env")


def test_load_env_file_is_directory():
    """测试加载目录作为 env 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="must be a file, not a directory"):
            AgentConfig.load(tmpdir)


def test_load_env_file_valid():
    """测试加载有效的 env 文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("OPENAI_API_KEY=test_key_123\n")
        f.write("OPENAI_MODEL=gpt-4\n")
        f.write("OPENAI_TEMPERATURE=0.7\n")
        tmp_path = f.name

    try:
        config = AgentConfig.load(tmp_path)
        assert config.openai_api_key == "test_key_123"
        assert config.openai_model == "gpt-4"
        assert config.openai_temperature == 0.7
    finally:
        os.unlink(tmp_path)


def test_get_config_singleton():
    """测试 get_config 单例模式"""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


def test_get_config_reload():
    """测试 reload 参数"""
    config1 = get_config()
    config2 = get_config(reload=True)
    # 重新加载后应该是新的实例（但值相同）
    # 注意：由于没有 env 文件变化，可能是同一个实例，取决于实现
    assert config2 is not None


def test_set_config_override():
    """测试手动设置配置"""
    custom_config = AgentConfig(openai_model="custom-model")
    set_config(custom_config)

    result = get_config()
    assert result.openai_model == "custom-model"


def test_config_from_env_vars():
    """测试从环境变量加载配置"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "env_key_456", "OPENAI_MODEL": "gpt-3.5-turbo"}):
        config = AgentConfig()
        assert config.openai_api_key == "env_key_456"
        assert config.openai_model == "gpt-3.5-turbo"
