import json
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
class Manifest:
    """项目生成状态持久化

    支持断点恢复，不重复生成
    """
    session_id: str
    project_name: str
    created_at: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    tasks: Dict[str, TaskState] = field(default_factory=dict)

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
        """从磁盘加载 Manifest"""
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tasks = {}
        for task_id, task_data in data.get("tasks", {}).items():
            files_data = task_data.pop("generated_files", [])
            files = [TaskFile(**f) for f in files_data]
            tasks[task_id] = TaskState(generated_files=files, **task_data)

        data["tasks"] = tasks
        return cls(**data)

    def save(self, path: Path) -> None:
        """保存到磁盘"""
        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_task(self, task_id: str, name: str, task_type: str = "unknown",
                 dependencies: List[str] = None) -> None:
        """添加任务"""
        self.tasks[task_id] = TaskState(
            id=task_id,
            name=name,
            type=task_type,
            dependencies=dependencies or [],
        )
        self.total_tasks = len(self.tasks)

    def start_task(self, task_id: str) -> None:
        """标记任务开始"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "running"
            self.tasks[task_id].started_at = datetime.now().isoformat()

    def complete_task(self, task_id: str, generated_files: List[TaskFile] = None) -> None:
        """标记任务完成"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "success"
            task.completed_at = datetime.now().isoformat()
            if generated_files:
                task.generated_files = generated_files
            self.completed_tasks += 1

    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = datetime.now().isoformat()
            self.failed_tasks += 1

    def get_pending_tasks(self) -> List[str]:
        """获取所有待执行的任务ID"""
        return [tid for tid, task in self.tasks.items() if task.status == "pending"]

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
