"""测试 FixAgent 工具函数"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.agents.fix_agent import (
    _create_list_project_files,
    _create_overwrite_file,
    _create_quick_lint_check,
    _create_quick_type_check,
    _create_read_file,
    _detect_lint_command,
    _detect_type_check_command,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestDetectLintCommand:
    """测试 lint 命令自动检测"""

    def test_detect_python_project(self, temp_dir):
        """Python 项目检测到 uv run ruff check"""
        (temp_dir / "pyproject.toml").touch()

        commands = _detect_lint_command(str(temp_dir))
        assert commands == ["uv run ruff check ."]

    def test_detect_js_project(self, temp_dir):
        """JS 项目检测到 npm run lint"""
        (temp_dir / "package.json").touch()

        commands = _detect_lint_command(str(temp_dir))
        assert commands == ["npm run lint"]

    def test_detect_no_config_file(self, temp_dir):
        """没有配置文件时返回空列表"""
        commands = _detect_lint_command(str(temp_dir))
        assert commands == []


class TestDetectTypeCheckCommand:
    """测试类型检查命令自动检测"""

    def test_detect_python_project(self, temp_dir):
        """Python 项目检测到 uv run mypy"""
        (temp_dir / "pyproject.toml").touch()

        commands = _detect_type_check_command(str(temp_dir))
        assert commands == ["uv run mypy ."]

    def test_detect_js_project(self, temp_dir):
        """JS 项目检测到 npm run type-check"""
        (temp_dir / "package.json").touch()

        commands = _detect_type_check_command(str(temp_dir))
        assert commands == ["npm run type-check"]

    def test_detect_no_config_file(self, temp_dir):
        """没有配置文件时返回空列表"""
        commands = _detect_type_check_command(str(temp_dir))
        assert commands == []


class TestReadFileTool:
    """测试 read_file 工具"""

    def test_read_file_success(self, temp_dir):
        """成功读取文件"""
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        read_file = _create_read_file(str(temp_dir))
        result = read_file.invoke({"file_path": "test.py"})

        assert result == "print('hello')"

    def test_read_file_not_exist(self, temp_dir):
        """文件不存在"""
        read_file = _create_read_file(str(temp_dir))
        result = read_file.invoke({"file_path": "not_exist.py"})

        assert "文件不存在" in result

    def test_read_file_is_directory(self, temp_dir):
        """路径是目录"""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        read_file = _create_read_file(str(temp_dir))
        result = read_file.invoke({"file_path": "subdir"})

        assert "不是文件" in result

    def test_read_file_path_traversal_blocked(self, temp_dir):
        """路径遍历攻击被阻止"""
        read_file = _create_read_file(str(temp_dir))
        result = read_file.invoke({"file_path": "../etc/passwd"})

        assert "Path traversal detected" in result or "路径遍历攻击" in result

    def test_read_file_empty_path(self, temp_dir):
        """空路径"""
        read_file = _create_read_file(str(temp_dir))
        result = read_file.invoke({"file_path": ""})

        assert "cannot be empty" in result or "空" in result


class TestOverwriteFileTool:
    """测试 overwrite_file 工具"""

    def test_overwrite_existing_file(self, temp_dir):
        """覆盖已有文件"""
        test_file = temp_dir / "test.py"
        test_file.write_text("old content")

        overwrite_file = _create_overwrite_file(str(temp_dir))
        result = overwrite_file.invoke({
            "file_path": "test.py",
            "content": "new content",
        })

        assert "文件已修复" in result
        assert test_file.read_text() == "new content"

    def test_overwrite_creates_new_file(self, temp_dir):
        """创建新文件（文件不存在）"""
        overwrite_file = _create_overwrite_file(str(temp_dir))
        result = overwrite_file.invoke({
            "file_path": "new_file.py",
            "content": "print('new')",
        })

        assert "文件已修复" in result
        assert (temp_dir / "new_file.py").read_text() == "print('new')"

    def test_overwrite_creates_subdirectory(self, temp_dir):
        """自动创建子目录"""
        overwrite_file = _create_overwrite_file(str(temp_dir))
        result = overwrite_file.invoke({
            "file_path": "subdir/nested/file.py",
            "content": "print('nested')",
        })

        assert "文件已修复" in result
        assert (temp_dir / "subdir/nested/file.py").read_text() == "print('nested')"

    def test_overwrite_path_traversal_blocked(self, temp_dir):
        """路径遍历攻击被阻止"""
        overwrite_file = _create_overwrite_file(str(temp_dir))
        result = overwrite_file.invoke({
            "file_path": "../malicious.py",
            "content": "evil code",
        })

        assert "Path traversal detected" in result or "路径遍历攻击" in result

    def test_overwrite_empty_path(self, temp_dir):
        """空路径"""
        overwrite_file = _create_overwrite_file(str(temp_dir))
        result = overwrite_file.invoke({
            "file_path": "",
            "content": "test",
        })

        assert "cannot be empty" in result or "空" in result


class TestListProjectFilesTool:
    """测试 list_project_files 工具"""

    def test_list_files(self, temp_dir):
        """列出项目文件"""
        (temp_dir / "file1.py").touch()
        (temp_dir / "file2.py").touch()
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").touch()

        list_files = _create_list_project_files(str(temp_dir))
        result = list_files.invoke({})

        assert "file1.py" in result
        assert "file2.py" in result
        assert "subdir/file3.py" in result

    def test_list_files_ignores_pycache(self, temp_dir):
        """忽略 __pycache__ 目录"""
        (temp_dir / "file.py").touch()
        pycache = temp_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "file.cpython-311.pyc").touch()

        list_files = _create_list_project_files(str(temp_dir))
        result = list_files.invoke({})

        assert "file.py" in result
        assert "__pycache__" not in result

    def test_list_files_empty_project(self, temp_dir):
        """空项目"""
        list_files = _create_list_project_files(str(temp_dir))
        result = list_files.invoke({})

        assert result == ""


class TestQuickLintCheckTool:
    """测试 quick_lint_check 工具"""

    def test_no_lint_command_detected(self, temp_dir):
        """未检测到 lint 命令"""
        check_lint = _create_quick_lint_check(str(temp_dir))
        result = check_lint.invoke({})

        assert "未检测到 lint 命令" in result

    def test_lint_success(self, temp_dir):
        """lint 检查通过"""
        (temp_dir / "pyproject.toml").touch()

        check_lint = _create_quick_lint_check(str(temp_dir))

        with patch("core.agents.fix_agent.run_shell_command", return_value=(True, "")):
            result = check_lint.invoke({})

        assert "✅ uv run ruff check . 检查通过" in result

    def test_lint_failure(self, temp_dir):
        """lint 检查失败"""
        (temp_dir / "pyproject.toml").touch()

        check_lint = _create_quick_lint_check(str(temp_dir))

        with patch("core.agents.fix_agent.run_shell_command", return_value=(False, "E123 syntax error")):
            result = check_lint.invoke({})

        assert "❌ uv run ruff check . 检查失败" in result
        assert "E123 syntax error" in result


class TestQuickTypeCheckTool:
    """测试 quick_type_check 工具"""

    def test_no_type_check_command_detected(self, temp_dir):
        """未检测到类型检查命令"""
        check_type = _create_quick_type_check(str(temp_dir))
        result = check_type.invoke({})

        assert "未检测到类型检查命令" in result

    def test_type_check_success(self, temp_dir):
        """类型检查通过"""
        (temp_dir / "pyproject.toml").touch()

        check_type = _create_quick_type_check(str(temp_dir))

        with patch("core.agents.fix_agent.run_shell_command", return_value=(True, "Success: no issues found")):
            result = check_type.invoke({})

        assert "✅ uv run mypy . 类型检查通过" in result

    def test_type_check_failure(self, temp_dir):
        """类型检查失败"""
        (temp_dir / "pyproject.toml").touch()

        check_type = _create_quick_type_check(str(temp_dir))

        with patch("core.agents.fix_agent.run_shell_command", return_value=(False, "Type error: incompatible type")):
            result = check_type.invoke({})

        assert "❌ uv run mypy . 类型检查失败" in result
        assert "incompatible type" in result


class TestFixAgentRunWithLog:
    """测试 FixAgent.run_with_log 方法"""

    def test_run_with_log_finished_normally(self, temp_dir):
        """调用了 finish 工具，认为正常完成"""
        from core.agents.fix_agent import FixAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.max_iterations = 10

        agent = FixAgent(mock_llm, str(temp_dir), mock_config)

        # Mock run 方法返回包含 finish 调用的结果
        with patch.object(agent, "run") as mock_run:
            mock_run.return_value = {
                "tools_called": ["read_file", "finish"],
            }

            result = agent.run_with_log("fix this error", verbose=True)

        assert result is True  # 调用了 finish，正常完成

    def test_run_with_log_force_terminated(self, temp_dir):
        """未调用 finish 工具，认为被强制终止"""
        from core.agents.fix_agent import FixAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.max_iterations = 10

        agent = FixAgent(mock_llm, str(temp_dir), mock_config)

        with patch.object(agent, "run") as mock_run:
            mock_run.return_value = {
                "tools_called": ["read_file", "overwrite_file"],  # 没有 finish
            }

            result = agent.run_with_log("fix this error", verbose=False)

        assert result is False  # 未调用 finish，被强制终止

    def test_run_with_log_no_tools_called(self, temp_dir):
        """没有调用任何工具"""
        from core.agents.fix_agent import FixAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.max_iterations = 10

        agent = FixAgent(mock_llm, str(temp_dir), mock_config)

        with patch.object(agent, "run") as mock_run:
            mock_run.return_value = {"tools_called": []}

            result = agent.run_with_log("fix this error", verbose=True)

        assert result is False
