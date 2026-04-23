"""快照管理模块 - 独立负责项目状态的备份与恢复

职责：
1. 创建项目快照（完整备份 + 文件清单）
2. 从快照恢复项目状态
3. 清理过期快照
4. 删除本轮新增文件
5. 清理空目录（从深到浅）
"""

import fnmatch
import os
import shutil
from pathlib import Path
from typing import List, Optional


def _iter_all_files(path: Path, ignore_check: bool = False) -> list[Path]:
    """迭代遍历所有文件，包括隐藏文件（避免递归栈溢出）

    使用 os.scandir 替代 Path.iterdir，性能提升约 2-3 倍。
    使用显式栈替代递归，避免深层目录导致的栈溢出问题。

    Args:
        path: 要遍历的目录
        ignore_check: 是否跳过忽略规则检查（用于恢复时遍历备份目录）
    """
    all_files = []
    stack = [str(path)]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    entry_path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if ignore_check or not _should_ignore_file(entry_path):
                            stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        if ignore_check or not _should_ignore_file(entry_path):
                            all_files.append(entry_path)
        except (PermissionError, OSError):
            # 无法访问的目录跳过
            continue

    return all_files


def _should_ignore_file(path: Path) -> bool:
    """判断文件/目录是否应该被忽略（快照和回滚时共用）"""
    ignore_dirs = {"__pycache__", ".backup", ".git", ".venv", "node_modules",
                   ".pytest_cache", "dist", "build", "target", ".idea", ".vscode"}
    ignore_patterns = {"*.pyc", "*.pyo", "*.pyd", ".DS_Store", ".filelist.txt"}

    if any(dir_name in path.parts for dir_name in ignore_dirs):
        return True
    if any(fnmatch.fnmatch(path.name, pattern) for pattern in ignore_patterns):
        return True
    return False


class SnapshotManager:
    """项目快照管理器

    提供原子性的快照创建、恢复、清理功能，
    是多轮自动修复的基础保障。
    """

    def __init__(self, working_dir: str | Path, session_id: Optional[str] = None):
        self.working_dir = Path(working_dir).resolve()
        self.session_id = session_id or "default"
        self.backup_root = self.working_dir / ".backup"

    def get_snapshot_name(self, attempt: int) -> str:
        """生成快照名称（包含 session_id，避免冲突）"""
        return f"{self.session_id}_snapshot_{attempt:03d}"

    def create_snapshot(self, snapshot_name: str) -> None:
        """创建项目完整快照

        Args:
            snapshot_name: 快照名称（不含路径）
        """
        backup_dir = self.backup_root / snapshot_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 收集所有需要备份的文件（包括隐藏文件！rglob("*") 会漏掉 . 开头的文件）
        project_files = _iter_all_files(self.working_dir)

        # 复制文件
        for src in project_files:
            rel_path = src.relative_to(self.working_dir)
            dst = backup_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 保存文件清单（用于回滚时识别新增文件）
        file_list = [str(p.relative_to(self.working_dir)) for p in project_files]
        with open(backup_dir / ".filelist.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(file_list))

    def restore_snapshot(self, snapshot_name: str) -> bool:
        """从快照恢复项目状态

        1. 恢复所有快照中存在的文件
        2. 删除本轮新增的文件（快照中不存在的文件）
        3. 清理因删除文件产生的空目录（从深到浅）

        Args:
            snapshot_name: 快照名称

        Returns:
            是否成功恢复（快照不存在时返回 False）
        """
        snapshot_dir = self.backup_root / snapshot_name
        if not snapshot_dir.exists():
            return False

        # 加载快照时的文件清单
        filelist_path = snapshot_dir / ".filelist.txt"
        if filelist_path.exists():
            with open(filelist_path, "r", encoding="utf-8") as f:
                snapshot_files = set(f.read().splitlines())
        else:
            snapshot_files = None

        # 恢复快照文件（使用 _iter_all_files，包括隐藏文件！）
        # ignore_check=True：备份目录本身是 .backup，不应该被忽略
        for src in _iter_all_files(snapshot_dir, ignore_check=True):
            rel_path = src.relative_to(snapshot_dir)
            dst = self.working_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # 删除本轮新增的文件（快照中不存在的文件）
        if snapshot_files is not None:
            new_files = []
            for p in _iter_all_files(self.working_dir):
                rel_path = str(p.relative_to(self.working_dir))
                if rel_path not in snapshot_files:
                    new_files.append(p)

            for p in new_files:
                p.unlink()

            # 清理因删除文件产生的空目录（从深到浅，避免父目录先空导致子目录找不到）
            # 用相对路径的深度排序，确保子目录总是比父目录先被处理
            all_dirs = []
            for p in self.working_dir.rglob("*"):
                if p.is_dir() and not _should_ignore_file(p):
                    rel_path = p.relative_to(self.working_dir)
                    depth = len(rel_path.parts)
                    all_dirs.append((depth, p))

            # 按深度从大到小排序
            for _, p in sorted(all_dirs, key=lambda x: -x[0]):
                if not any(p.iterdir()):
                    try:
                        p.rmdir()
                    except OSError:
                        pass  # 目录非空或无权限，忽略

        return True

    def cleanup_snapshots(self, keep_list: Optional[List[str]] = None) -> None:
        """清理快照，只保留列表中的

        Args:
            keep_list: 要保留的快照名称列表，None 表示全部清理
        """
        if not self.backup_root.exists():
            return

        for item in self.backup_root.iterdir():
            if item.is_dir() and (keep_list is None or item.name not in keep_list):
                try:
                    shutil.rmtree(item)
                except OSError:
                    pass  # 文件被占用或无权限，忽略

        # 清理完成后，如果目录为空，删除目录本身
        try:
            if not any(self.backup_root.iterdir()):
                self.backup_root.rmdir()
        except OSError:
            pass  # 目录非空或无权限，忽略

    def snapshot_exists(self, snapshot_name: str) -> bool:
        """检查快照是否存在"""
        return (self.backup_root / snapshot_name).exists()
