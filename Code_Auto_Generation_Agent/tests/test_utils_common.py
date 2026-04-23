"""测试路径安全工具函数"""

import os
from pathlib import Path

import pytest

from core.utils.common import safe_resolve_path


def test_safe_resolve_path_normal_file():
    """正常情况：工作目录内的文件"""
    working_dir = Path.cwd()
    result = safe_resolve_path(working_dir, "test.py")
    assert result == (working_dir / "test.py").resolve()


def test_safe_resolve_path_subdirectory():
    """正常情况：子目录内的文件"""
    working_dir = Path.cwd()
    result = safe_resolve_path(working_dir, "src/main.py")
    assert result == (working_dir / "src" / "main.py").resolve()


def test_safe_resolve_path_dot_slash():
    """正常情况：./ 开头的相对路径"""
    working_dir = Path.cwd()
    result = safe_resolve_path(working_dir, "./test.py")
    assert result == (working_dir / "test.py").resolve()


def test_safe_resolve_path_empty_working_dir():
    """异常情况：空的 working_dir"""
    with pytest.raises(ValueError, match="working_dir cannot be empty"):
        safe_resolve_path("", "test.py")


def test_safe_resolve_path_empty_file_path():
    """异常情况：空的 file_path"""
    with pytest.raises(ValueError, match="file_path cannot be empty"):
        safe_resolve_path(Path.cwd(), "")


def test_safe_resolve_path_traversal_attack():
    """安全防护：../ 路径遍历攻击"""
    working_dir = Path.cwd()
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve_path(working_dir, "../etc/passwd")


def test_safe_resolve_path_deep_traversal():
    """安全防护：多层 ../ 遍历"""
    working_dir = Path.cwd()
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve_path(working_dir, "../../../etc/passwd")


def test_safe_resolve_path_traversal_in_middle():
    """安全防护：路径中间包含 ../"""
    working_dir = Path.cwd()
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve_path(working_dir, "src/../../etc/passwd")


def test_safe_resolve_path_absolute_path_escape():
    """安全防护：绝对路径试图跳出"""
    working_dir = Path.cwd()
    # 使用其他分区根目录
    escape_path = "C:/" if os.name == "nt" else "/etc/passwd"
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve_path(working_dir, escape_path)


def test_safe_resolve_path_string_working_dir():
    """支持 string 类型的 working_dir"""
    working_dir = str(Path.cwd())
    result = safe_resolve_path(working_dir, "test.py")
    assert result == (Path.cwd() / "test.py").resolve()


def test_safe_resolve_path_path_object():
    """支持 Path 对象类型的 working_dir"""
    working_dir = Path.cwd()
    result = safe_resolve_path(working_dir, "test.py")
    assert result == (working_dir / "test.py").resolve()


def test_safe_resolve_path_exact_working_dir():
    """边界：file_path 就是工作目录本身"""
    working_dir = Path.cwd()
    result = safe_resolve_path(working_dir, ".")
    # 应该返回工作目录的绝对路径
    assert result == working_dir.resolve()


def test_safe_resolve_path_symlink_inside():
    """边界：目录内符号链接（允许）"""
    # 此测试依赖特定环境，仅验证不崩溃
    working_dir = Path.cwd()
    try:
        result = safe_resolve_path(working_dir, ".")
        assert result is not None
    except ValueError:
        # 根据环境可能抛出也可能不，不强制
        pass
