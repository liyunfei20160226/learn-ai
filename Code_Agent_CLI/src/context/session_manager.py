"""
SessionManager - 会话管理器（对齐 Claude Code 设计）

职责：
1. 生成唯一 sessionId
2. 自动保存/加载会话
3. 维护全局历史索引 history.jsonl
4. 列出 / 删除会话

设计原则：
- 所有会话全局存储：~/.code-agent/sessions/
- 每个会话记录 cwd（创建时的工作目录）
- 不做自动清理，永久保留，删除完全用户手动控制
- 每轮对话结束后自动保存，不需要用户手动 save
"""
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.console import Console


class SessionManager:
    """会话管理器"""

    def __init__(self, sessions_dir: Optional[str] = None):
        # 默认全局位置：~/.code-agent/sessions
        default_dir = Path.home() / ".code-agent" / "sessions"
        self.sessions_dir = Path(sessions_dir or default_dir)
        self.history_path = self.sessions_dir.parent / "history.jsonl"
        # 注意：_ensure_dirs() 不在这里调用，改为惰性创建（第一次 save 时才创建）
        # 这样如果用户什么都没说就退出，不会留下空目录和文件

    def _ensure_dirs(self) -> None:
        """确保目录存在"""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.touch()

    def generate_session_id(self) -> str:
        """生成 UUID 风格的会话 ID（前 8 位，兼顾简洁和唯一性）"""
        return uuid.uuid4().hex[:8]

    def _get_session_file_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.sessions_dir / f"{session_id}.session.json"

    def _read_history(self) -> List[Dict[str, Any]]:
        """读取历史索引"""
        entries: List[Dict[str, Any]] = []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            pass
        return entries

    def _write_history(self, entries: List[Dict[str, Any]]) -> None:
        """写入历史索引"""
        self._ensure_dirs()  # 确保目录存在（防止 rename_session 时直接调用）
        with open(self.history_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _update_history_entry(
        self,
        session_id: str,
        name: str,
        cwd: str,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ) -> None:
        """更新或创建历史索引条目"""
        entries = self._read_history()

        # 查找是否已存在
        existing_idx = None
        for i, entry in enumerate(entries):
            if entry.get("session_id") == session_id:
                existing_idx = i
                break

        now = time.time()
        if existing_idx is not None:
            # 更新
            entries[existing_idx]["name"] = name
            entries[existing_idx]["updated_at"] = updated_at or now
            entries[existing_idx]["cwd"] = cwd
        else:
            # 新建
            entries.append({
                "session_id": session_id,
                "name": name,
                "created_at": created_at or now,
                "updated_at": updated_at or now,
                "cwd": cwd,
            })

        self._write_history(entries)

    def save_session(
        self,
        session_id: str,
        name: str,
        memory_data: Dict[str, Any],
        tool_buffer_data: Dict[str, Any],
        cwd: str,
    ) -> None:
        """
        保存当前会话（自动调用，每轮对话结束后执行）

        Args:
            session_id: 会话 ID
            name: 会话名称（用户可通过 /save 改名）
            memory_data: MemoryLayer 的序列化数据
            tool_buffer_data: ToolResultBufferLayer 的序列化数据
            cwd: 当前工作目录
        """
        # 🚀 惰性创建：第一次真正需要保存时才创建目录和文件
        self._ensure_dirs()

        file_path = self._get_session_file_path(session_id)

        # 读取现有会话获取创建时间（如果存在）
        created_at = time.time()
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    created_at = existing.get("created_at", created_at)
            except Exception:
                pass

        data = {
            "version": 1,
            "session_id": session_id,
            "name": name,
            "created_at": created_at,
            "updated_at": time.time(),
            "cwd": cwd,
            "working_turns": memory_data.get("working_turns", 3),
            "short_term_turns": memory_data.get("short_term_turns", 10),
            "turns": memory_data.get("turns", []),
            "tool_buffer_state": tool_buffer_data,
        }

        # 保存到会话文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新历史索引
        self._update_history_entry(
            session_id=session_id,
            name=name,
            cwd=cwd,
            created_at=created_at,
            updated_at=data["updated_at"],
        )

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定会话

        Returns:
            会话数据字典，找不到返回 None
        """
        file_path = self._get_session_file_path(session_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            Console.error(f"加载会话失败: {e}")
            return None

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        列出所有历史会话（从 history.jsonl 读取，O(1) 加载）

        Args:
            limit: 返回最近多少条

        Returns:
            按更新时间降序排列的会话列表
        """
        entries = self._read_history()

        # 按 updated_at 降序（最新的在前面）
        entries.sort(key=lambda x: x.get("updated_at", 0), reverse=True)

        return entries[:limit]

    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话（同时删除文件 + 更新索引）

        Returns:
            是否删除成功
        """
        # 删除文件
        file_path = self._get_session_file_path(session_id)
        if file_path.exists():
            file_path.unlink()

        # 从索引中移除
        entries = self._read_history()
        entries = [e for e in entries if e.get("session_id") != session_id]
        self._write_history(entries)

        return True

    def get_last_session(self) -> Optional[str]:
        """
        获取最近的一个 session id（用于 /resume 命令）

        Returns:
            最近的 session id，找不到返回 None
        """
        entries = self.list_sessions(limit=1)
        if entries:
            return entries[0].get("session_id")
        return None

    def rename_session(self, session_id: str, name: str) -> None:
        """
        给会话改名（/save 命令本质是改名）

        注意：这只是改个显示名称，方便用户在列表里认出来，
        实际会话数据已经在每轮对话后自动保存了。
        """
        # 先从历史索引中读取现有数据
        entries = self._read_history()
        cwd = str(Path.cwd())
        created_at = time.time()

        for entry in entries:
            if entry.get("session_id") == session_id:
                cwd = entry.get("cwd", cwd)
                created_at = entry.get("created_at", created_at)
                break

        # 更新历史索引
        self._update_history_entry(
            session_id=session_id,
            name=name,
            cwd=cwd,
            created_at=created_at,
        )

        # 同时更新会话文件里的 name 字段
        file_path = self._get_session_file_path(session_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["name"] = name
                data["updated_at"] = time.time()
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                Console.error(f"更新会话名称失败: {e}")
