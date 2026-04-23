"""测试 CodegenAgent 工具函数"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.agents.codegen_agent import (
    _create_append_file,
    _create_finish,
    _create_list_generated_files,
    _create_overwrite_file,
    _create_read_file,
    _create_write_file,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def generated_files():
    return []


def noop_normalize(path):
    """不做任何处理的 normalize 函数"""
    return path


class TestWriteFileTool:
    """测试 write_file 工具"""

    def test_write_new_file(self, temp_dir, generated_files):
        """写入新文件"""
        write_file = _create_write_file(str(temp_dir), generated_files, noop_normalize)

        result = write_file.invoke({
            "file_path": "test.py",
            "content": "print('hello')",
        })

        assert "文件已写入" in result
        assert "test.py" in result
        assert (temp_dir / "test.py").read_text() == "print('hello')"

        # 检查是否记录在 generated_files 中
        assert len(generated_files) == 1
        assert generated_files[0]["file_path"] == "test.py"
        assert "content_sha" in generated_files[0]

    def test_write_file_creates_subdirectory(self, temp_dir, generated_files):
        """自动创建子目录"""
        write_file = _create_write_file(str(temp_dir), generated_files, noop_normalize)

        write_file.invoke({
            "file_path": "src/app/main.py",
            "content": "main content",
        })

        assert (temp_dir / "src/app/main.py").exists()
        assert len(generated_files) == 1

    def test_write_file_overwrites_existing(self, temp_dir, generated_files):
        """覆盖已存在的文件"""
        test_file = temp_dir / "test.py"
        test_file.write_text("old content")

        write_file = _create_write_file(str(temp_dir), generated_files, noop_normalize)
        write_file.invoke({
            "file_path": "test.py",
            "content": "new content",
        })

        assert test_file.read_text() == "new content"

    def test_write_file_content_hash(self, temp_dir, generated_files):
        """检查 content_sha 哈希是否正确"""
        write_file = _create_write_file(str(temp_dir), generated_files, noop_normalize)

        content = "print('hello')"
        write_file.invoke({
            "file_path": "test.py",
            "content": content,
        })

        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        assert generated_files[0]["content_sha"] == expected_hash


class TestAppendFileTool:
    """测试 append_file 工具"""

    def test_append_to_existing_file(self, temp_dir):
        """向已存在的文件追加内容"""
        test_file = temp_dir / "test.py"
        test_file.write_text("line1\n")

        append_file = _create_append_file(str(temp_dir), noop_normalize)
        result = append_file.invoke({
            "file_path": "test.py",
            "content": "line2\n",
        })

        assert "已追加内容" in result
        assert test_file.read_text() == "line1\nline2\n"

    def test_append_to_nonexistent_file_fails(self, temp_dir):
        """向不存在的文件追加会失败"""
        append_file = _create_append_file(str(temp_dir), noop_normalize)
        result = append_file.invoke({
            "file_path": "not_exist.py",
            "content": "test",
        })

        assert "文件不存在" in result


class TestReadFileTool:
    """测试 read_file 工具"""

    def test_read_existing_file(self, temp_dir):
        """读取已存在的文件"""
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        read_file = _create_read_file(str(temp_dir), noop_normalize)
        result = read_file.invoke({"file_path": "test.py"})

        assert result == "print('hello')"

    def test_read_nonexistent_file(self, temp_dir):
        """读取不存在的文件"""
        read_file = _create_read_file(str(temp_dir), noop_normalize)
        result = read_file.invoke({"file_path": "not_exist.py"})

        assert "文件不存在" in result


class TestListGeneratedFilesTool:
    """测试 list_generated_files 工具"""

    def test_no_files_generated(self, generated_files):
        """没有生成文件时"""
        list_files = _create_list_generated_files(generated_files)
        result = list_files.invoke({})

        assert "暂无已生成文件" in result

    def test_has_generated_files(self, generated_files):
        """有已生成文件时"""
        generated_files.extend([
            {"file_path": "test1.py", "content_sha": "abc"},
            {"file_path": "subdir/test2.py", "content_sha": "def"},
        ])

        list_files = _create_list_generated_files(generated_files)
        result = list_files.invoke({})

        assert "已生成文件" in result
        assert "test1.py" in result
        assert "subdir/test2.py" in result


class TestFinishTool:
    """测试 finish 工具"""

    def test_finish_with_files(self, generated_files):
        """有文件生成时"""
        generated_files.extend([
            {"file_path": "test1.py", "content_sha": "abc"},
            {"file_path": "test2.py", "content_sha": "def"},
        ])

        finish = _create_finish(generated_files)
        result = finish.invoke({"summary": "All files created!"})

        assert "代码生成完成" in result
        assert "共生成 2 个文件" in result
        assert "All files created!" in result

    def test_finish_without_files(self, generated_files):
        """没有生成文件时"""
        finish = _create_finish(generated_files)
        result = finish.invoke({"summary": "Done!"})

        assert "共生成 0 个文件" in result


class TestOverwriteFileTool:
    """测试 overwrite_file 工具（是 write_file 的别名）"""

    def test_overwrite_is_same_as_write(self, temp_dir, generated_files):
        """overwrite_file 应该和 write_file 行为一致"""
        write_file = _create_write_file(str(temp_dir), generated_files, noop_normalize)
        overwrite_file = _create_overwrite_file(write_file)

        # 调用 overwrite_file
        result = overwrite_file.invoke({
            "file_path": "test.py",
            "content": "overwritten",
        })

        assert "文件已写入" in result
        assert (temp_dir / "test.py").read_text() == "overwritten"
        assert len(generated_files) == 1


class TestNormalizeFilePath:
    """测试 _normalize_file_path 方法"""

    def test_normalize_simple_path(self, temp_dir):
        """简单路径不做修改"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        result = agent._normalize_file_path("app/main.py")
        assert result == "app/main.py"

    def test_normalize_removes_redundant_prefix(self, temp_dir):
        """移除重复的路径前缀"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None

        # 在 temp_dir 下创建子目录模拟工作目录
        backend_dir = temp_dir / "backend"
        backend_dir.mkdir()

        agent = CodegenAgent(mock_llm, str(backend_dir), mock_config)

        # LLM 可能会错误地加上 backend 前缀
        result = agent._normalize_file_path("backend/app/main.py")
        # 应该被规范化为 app/main.py
        assert result == "app/main.py"

    def test_normalize_preserves_nested(self, temp_dir):
        """嵌套路径应该被保留"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        result = agent._normalize_file_path("a/b/c/d/e.py")
        assert result == "a/b/c/d/e.py"


class TestGetGeneratedFiles:
    """测试 get_generated_files 方法"""

    def test_returns_copy(self, temp_dir):
        """返回列表副本，防止外部修改内部状态"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        # 向内部引用添加文件
        agent._generated_files_ref.append({"file_path": "test.py"})

        # 获取外部引用
        external_ref = agent.get_generated_files()
        assert len(external_ref) == 1

        # 修改外部列表，不应该影响内部
        external_ref.append({"file_path": "fake.py"})
        assert len(agent._generated_files_ref) == 1


class TestCodegenAgentInit:
    """测试 CodegenAgent 初始化"""

    def test_init_tools(self, temp_dir):
        """测试初始化时创建的工具"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None

        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        # 应该有 10 个工具（4 个基类工具 + 6 个子类工具）
        assert len(agent.tools) == 10
        tool_names = [t.name for t in agent.tools]
        assert "write_file" in tool_names
        assert "append_file" in tool_names
        assert "overwrite_file" in tool_names
        assert "read_file" in tool_names
        assert "list_generated_files" in tool_names
        assert "finish" in tool_names

    def test_init_generated_files_empty(self, temp_dir):
        """初始时 generated_files 为空"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        assert agent.get_generated_files() == []


class TestRunWithLog:
    """测试 run_with_log 方法"""

    def test_run_with_log_returns_generated_files(self, temp_dir):
        """返回生成的文件列表"""
        from core.agents.codegen_agent import CodegenAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None
        mock_config.max_iterations = 10

        agent = CodegenAgent(mock_llm, str(temp_dir), mock_config)

        # 模拟生成文件
        agent._generated_files_ref.extend([
            {"file_path": "test1.py", "content_sha": "abc"},
            {"file_path": "test2.py", "content_sha": "def"},
        ])

        # Mock run 方法
        with patch.object(agent, "run"):
            result = agent.run_with_log("generate code", verbose=False)

        assert len(result) == 2
        assert result[0]["file_path"] == "test1.py"
        assert result[1]["file_path"] == "test2.py"


from unittest.mock import patch
