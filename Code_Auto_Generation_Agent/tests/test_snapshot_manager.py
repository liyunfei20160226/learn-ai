"""测试快照管理模块"""

import os
import tempfile
from pathlib import Path

from core.snapshot_manager import SnapshotManager, _iter_all_files, _should_ignore_file


def test_should_ignore_file_ignored_dirs():
    """测试忽略目录中的文件"""
    path = Path("__pycache__/test.pyc")
    assert _should_ignore_file(path) is True

    path = Path("src/.git/config")
    assert _should_ignore_file(path) is True

    path = Path("project/node_modules/package.json")
    assert _should_ignore_file(path) is True


def test_should_ignore_file_ignored_patterns():
    """测试忽略文件模式"""
    path = Path("test.pyc")
    assert _should_ignore_file(path) is True

    path = Path(".DS_Store")
    assert _should_ignore_file(path) is True

    path = Path("subdir/.filelist.txt")
    assert _should_ignore_file(path) is True


def test_should_ignore_file_normal_files():
    """测试正常文件不被忽略"""
    path = Path("main.py")
    assert _should_ignore_file(path) is False

    path = Path("src/utils.py")
    assert _should_ignore_file(path) is False

    path = Path("README.md")
    assert _should_ignore_file(path) is False


def test_iter_all_files():
    """测试迭代目录下所有文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 创建测试文件
        (tmp_path / "file1.py").touch()
        (tmp_path / "file2.py").touch()

        # 创建子目录和文件
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").touch()

        # 创建应该被忽略的目录
        ignored_dir = tmp_path / "__pycache__"
        ignored_dir.mkdir()
        (ignored_dir / "cache.pyc").touch()

        files = _iter_all_files(tmp_path)

        # 应该找到 3 个文件（忽略 __pycache__ 目录）
        file_names = {f.name for f in files}
        assert "file1.py" in file_names
        assert "file2.py" in file_names
        assert "file3.py" in file_names
        assert "cache.pyc" not in file_names


def test_snapshot_manager_basic():
    """测试快照管理器基本功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        manager = SnapshotManager(tmp_path, session_id="test")

        assert manager.working_dir == tmp_path.resolve()
        assert manager.session_id == "test"
        assert manager.backup_root == tmp_path.resolve() / ".backup"


def test_snapshot_manager_get_snapshot_name():
    """测试生成快照名称"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SnapshotManager(tmpdir, session_id="test_session")

        name = manager.get_snapshot_name(1)
        assert name == "test_session_snapshot_001"

        name = manager.get_snapshot_name(10)
        assert name == "test_session_snapshot_010"


def test_snapshot_manager_create_and_restore():
    """测试创建和恢复快照"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        # 创建初始文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        # 创建快照
        manager.create_snapshot("snap1")

        # 验证快照文件存在
        assert manager.snapshot_exists("snap1")
        assert (manager.backup_root / "snap1" / "test.py").exists()

        # 修改文件
        test_file.write_text("print('modified')")

        # 恢复快照
        result = manager.restore_snapshot("snap1")
        assert result is True

        # 验证文件被恢复
        assert test_file.read_text() == "print('hello')"


def test_snapshot_manager_restore_nonexistent():
    """测试恢复不存在的快照"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SnapshotManager(tmpdir, session_id="test")

        result = manager.restore_snapshot("nonexistent")
        assert result is False


def test_snapshot_manager_cleanup():
    """测试清理快照"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        # 创建多个快照
        manager.create_snapshot("snap1")
        manager.create_snapshot("snap2")
        manager.create_snapshot("snap3")

        assert manager.snapshot_exists("snap1")
        assert manager.snapshot_exists("snap2")
        assert manager.snapshot_exists("snap3")

        # 只保留 snap2
        manager.cleanup_snapshots(keep_list=["snap2"])

        assert not manager.snapshot_exists("snap1")
        assert manager.snapshot_exists("snap2")
        assert not manager.snapshot_exists("snap3")


def test_snapshot_manager_cleanup_all():
    """测试清理所有快照"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        manager.create_snapshot("snap1")
        manager.create_snapshot("snap2")

        # keep_list=None 清理全部
        manager.cleanup_snapshots(keep_list=None)

        assert not manager.snapshot_exists("snap1")
        assert not manager.snapshot_exists("snap2")


def test_snapshot_manager_cleanup_empty_backup_root():
    """测试清理不存在的备份目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SnapshotManager(tmpdir, session_id="test")

        # 不应该抛出异常
        manager.cleanup_snapshots()


def test_snapshot_restore_deletes_new_files():
    """测试快照恢复时删除新增文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        # 创建初始文件
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        # 创建快照
        manager.create_snapshot("snap1")

        # 新增文件
        new_file = tmp_path / "new_file.py"
        new_file.write_text("new content")

        assert new_file.exists()

        # 恢复快照
        manager.restore_snapshot("snap1")

        # 新增文件应该被删除
        assert not new_file.exists()
        assert test_file.exists()


def test_snapshot_restore_cleans_up_empty_dirs():
    """测试快照恢复时清理空目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        # 创建初始文件（无新目录）
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        # 创建快照
        manager.create_snapshot("snap1")

        # 新增目录和文件
        new_dir = tmp_path / "new_dir"
        new_dir.mkdir()
        new_file = new_dir / "new_file.py"
        new_file.write_text("new")

        assert new_dir.exists()
        assert new_file.exists()

        # 恢复快照
        manager.restore_snapshot("snap1")

        # 新增文件和目录应该被删除
        assert not new_file.exists()
        assert not new_dir.exists()


def test_snapshot_creates_hidden_files():
    """测试快照包含隐藏文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        manager = SnapshotManager(tmp_path, session_id="test")

        # 创建隐藏文件
        hidden_file = tmp_path / ".gitignore"
        hidden_file.write_text("*.pyc")

        # 创建快照
        manager.create_snapshot("snap1")

        # 删除隐藏文件
        hidden_file.unlink()

        # 恢复
        manager.restore_snapshot("snap1")

        # 隐藏文件应该被恢复
        assert hidden_file.exists()
        assert hidden_file.read_text() == "*.pyc"
