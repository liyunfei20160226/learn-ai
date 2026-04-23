"""测试 Shell 命令执行工具

注意：run_shell_command 主要集成了 subprocess，这里只测试
参数解析、异常处理等纯逻辑部分，不实际执行命令。
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.utils.shell import run_shell_command


def test_run_shell_command_success():
    """测试命令执行成功"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        success, output = run_shell_command("echo hello", Path.cwd())

    assert success is True
    assert output == "output"


def test_run_shell_command_failure():
    """测试命令执行失败"""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "error"

    with patch("subprocess.run", return_value=mock_result):
        success, output = run_shell_command("false", Path.cwd())

    assert success is False
    assert output == "error"


def test_run_shell_command_timeout():
    """测试命令超时"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
        success, output = run_shell_command("sleep 10", Path.cwd(), timeout=1)

    assert success is False
    assert "超时" in output


def test_run_shell_command_timeout_with_partial_output():
    """测试超时但有部分输出"""
    # 注意：不同 Python 版本的 TimeoutExpired 构造函数签名不同
    exc = subprocess.TimeoutExpired("cmd", 1)
    exc.stdout = b"partial"
    exc.stderr = b"error"

    with patch("subprocess.run", side_effect=exc):
        success, output = run_shell_command("sleep 10", Path.cwd(), timeout=1)

    assert success is False
    assert "partial" in output
    assert "error" in output


def test_run_shell_command_file_not_found():
    """测试命令不存在"""
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        success, output = run_shell_command("nonexistent_command_xyz", Path.cwd())

    assert success is False
    assert "不存在" in output


def test_run_shell_command_permission_error():
    """测试权限不足"""
    with patch("subprocess.run", side_effect=PermissionError()):
        success, output = run_shell_command("some_cmd", Path.cwd())

    assert success is False
    assert "权限" in output


def test_run_shell_command_pipe_auto_shell():
    """包含管道的命令自动使用 shell=True"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "hello"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        success, output = run_shell_command("echo hello | grep h", Path.cwd())

    assert success is True
    # 验证使用了 shell=True
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("shell") is True


def test_run_shell_command_redirect_auto_shell():
    """包含重定向的命令自动使用 shell=True"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        success, output = run_shell_command("echo hello > /dev/null", Path.cwd())

    assert success is True
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("shell") is True


def test_run_shell_command_simple_no_shell():
    """简单命令不使用 shell"""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        success, output = run_shell_command("echo hello", Path.cwd())

    assert success is True
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("shell") is False


def test_run_shell_command_generic_exception():
    """测试其他未知异常"""
    with patch("subprocess.run", side_effect=RuntimeError("unknown error")):
        success, output = run_shell_command("some_cmd", Path.cwd())

    assert success is False
    assert "RuntimeError" in output
