import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TaskFile:
    """任务生成的单个文件"""
    file_path: str
    content_sha: str = ""


@dataclass
class TaskState:
    """单个任务的状态"""
    id: str
    name: str
    type: str = "unknown"
    status: str = "pending"  # pending, running, success, failed
    dependencies: List[str] = field(default_factory=list)
    generated_files: List[TaskFile] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class FixAttempt:
    """单次修复尝试记录"""
    attempt: int                  # 第 N 轮
    failed_step: str              # 失败的步骤
    errors_before: int            # 修复前错误数量
    errors_after: int             # 修复后错误数量
    error_samples: List[str]      # 错误样例（前5条）
    timestamp: str                # 时间戳
    accepted: bool = False        # 是否接受这次修复（错误减少了）


@dataclass
class FixState:
    """自动修复状态"""
    enabled: bool = False
    current_attempt: int = 0
    max_attempts: int = 20

    # 最佳状态追踪
    best_attempt: int = 0         # 错误最少的那次
    best_error_count: int = 0     # 最少错误数量
    initial_error_count: int = 0  # 初始错误数量（基准线）

    # 当前状态
    last_failed_step: Optional[str] = None
    last_errors: List[str] = field(default_factory=list)

    # 质量检查命令（只生成一次，复用）
    check_commands: Dict[str, List[str]] = field(default_factory=dict)

    # 历史记录
    history: List[FixAttempt] = field(default_factory=list)

    # 最终状态
    status: str = "pending"       # pending, running, success, partial_success, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Manifest:
    """项目生成状态持久化

    支持断点恢复，不重复生成
    """
    session_id: str
    project_name: str
    created_at: str
    tasks: Dict[str, TaskState] = field(default_factory=dict)
    fix_state: Optional[FixState] = None  # 自动修复状态

    # 使用属性实时计算，避免字段不一致
    @property
    def total_tasks(self) -> int:
        """总任务数"""
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        """已完成任务数"""
        return sum(1 for t in self.tasks.values() if t.status == "success")

    @property
    def failed_tasks(self) -> int:
        """失败任务数"""
        return sum(1 for t in self.tasks.values() if t.status == "failed")

    @classmethod
    def create(cls, project_name: str = "Untitled") -> "Manifest":
        """创建新的 Manifest"""
        now = datetime.now()
        session_id = now.strftime("%Y%m%d_%H%M%S")
        return cls(
            session_id=session_id,
            project_name=project_name,
            created_at=now.isoformat(),
        )

    @classmethod
    def load(cls, path: Path) -> Optional["Manifest"]:
        """从磁盘加载 Manifest（复用 from_json 逻辑，避免代码重复）"""
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Manifest":
        """从 JSON 字符串反序列化（包装 load 方法）"""
        data = json.loads(json_str)

        # 处理 tasks
        tasks = {}
        for task_id, task_data in data.get("tasks", {}).items():
            files_data = task_data.pop("generated_files", [])
            if not isinstance(files_data, list):
                files_data = []
            files = [TaskFile(**f) for f in files_data]
            tasks[task_id] = TaskState(generated_files=files, **task_data)

        data["tasks"] = tasks

        # 处理 fix_state（嵌套 dataclass）
        fix_state_data = data.pop("fix_state", None)
        if fix_state_data:
            history_data = fix_state_data.pop("history", [])
            if isinstance(history_data, list):
                history = [FixAttempt(**item) for item in history_data]
            else:
                history = []
            fix_state_data["history"] = history
            data["fix_state"] = FixState(**fix_state_data)

        return cls(**data)

    def save(self, path: Path) -> None:
        """原子化保存到磁盘，防止崩溃损坏文件

        先写入临时文件（带随机UUID），成功后再 rename，保证原子性和多进程安全。
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f".{uuid.uuid4().hex}.tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
            f.flush()
            os.fsync(f.fileno())

        try:
            os.replace(temp_path, path)
        except Exception:
            # 发生异常时清理临时文件
            temp_path.unlink(missing_ok=True)
            raise

    def add_task(self, task_id: str, name: str, task_type: str = "unknown",
                 dependencies: Optional[List[str]] = None) -> None:
        """添加任务"""
        self.tasks[task_id] = TaskState(
            id=task_id,
            name=name,
            type=task_type,
            dependencies=dependencies or [],
        )
        # total_tasks 现在由属性自动计算，无需手动设置

    def start_task(self, task_id: str) -> None:
        """标记任务开始（幂等）
        已完成/已失败的任务状态不会被修改
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            # 终态任务不修改状态
            if task.status in ("success", "failed"):
                return
            task.status = "running"
            task.started_at = datetime.now().isoformat()

    def complete_task(self, task_id: str, generated_files: Optional[List[TaskFile]] = None) -> None:
        """标记任务完成（幂等）"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == "success":
                # 已完成任务不做任何修改，保持幂等性
                return
            task.status = "success"
            task.completed_at = datetime.now().isoformat()
            if generated_files:
                task.generated_files = generated_files
            # 使用属性实时计算，避免累加错误

    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败（幂等）"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == "failed":
                # 已失败任务不做任何修改，保持幂等性
                return
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.now().isoformat()
            # 使用属性实时计算，避免累加错误

    def get_pending_tasks(self) -> List[str]:
        """获取所有待执行的任务ID（包括崩溃恢复的 running 状态任务）"""
        # running 状态视为需要重试（崩溃恢复）
        return [tid for tid, task in self.tasks.items()
                if task.status in ("pending", "running")]

    def is_task_completed(self, task_id: str) -> bool:
        """检查任务是否已完成"""
        return task_id in self.tasks and self.tasks[task_id].status == "success"

    def get_completed_files(self) -> Dict[str, List[TaskFile]]:
        """获取所有已完成任务的文件列表"""
        result = {}
        for task_id, task in self.tasks.items():
            if task.status == "success" and task.generated_files:
                result[task_id] = task.generated_files
        return result
