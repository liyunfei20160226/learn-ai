"""
Task Manager for AutoPRD Web UI
Manages background tasks, logs, and output files
"""

import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

# Add project root to path so we can import autoprd
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class Task:
    task_id: str
    requirement: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    output_dir: Optional[Path] = None
    error: Optional[str] = None
    thread: Optional[threading.Thread] = None
    should_stop: bool = False

    @property
    def output_files(self) -> List[str]:
        """Return list of output files available for download"""
        if not self.output_dir or not self.output_dir.exists():
            return []
        return [f.name for f in self.output_dir.iterdir() if f.is_file()]


class TaskManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

        # Create output base directory
        self.output_base = project_root / "output" / "web"
        self.output_base.mkdir(parents=True, exist_ok=True)

    def create_task(self, requirement: str, custom_name: str | None = None) -> Task:
        """Create a new task

        Args:
            requirement: User requirement description
            custom_name: Optional custom directory name for output
        """
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            task_id=task_id,
            requirement=requirement,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
        )
        # Create output directory
        if custom_name and custom_name.strip():
            # Sanitize: only keep the last component if path contains slashes
            clean_name = custom_name.strip()
            # Extract basename after any path separators
            if '/' in clean_name:
                clean_name = clean_name.split('/')[-1]
            if '\\' in clean_name:
                clean_name = clean_name.split('\\')[-1]
            # Use cleaned custom name as directory name
            task.output_dir = self.output_base / clean_name
        else:
            # Fallback to task_id for backward compatibility
            task.output_dir = self.output_base / task_id
        task.output_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self._lock:
            return self.tasks.get(task_id)

    def start_task(self, task_id: str, func: Callable[[Task], None]) -> bool:
        """Start task in background thread"""
        task = self.get_task(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        thread = threading.Thread(target=func, args=(task,), daemon=True)
        task.thread = thread
        thread.start()
        return True

    def add_log(self, task_id: str, message: str):
        """Add log message to task"""
        task = self.get_task(task_id)
        if task:
            with self._lock:
                task.logs.append(message)

    def complete_task(self, task_id: str):
        """Mark task as completed"""
        task = self.get_task(task_id)
        if task:
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()

    def fail_task(self, task_id: str, error: str):
        """Mark task as failed"""
        task = self.get_task(task_id)
        if task:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error = error
                task.completed_at = datetime.now()

    def stop_task(self, task_id: str) -> bool:
        """Request task to stop"""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            with self._lock:
                task.should_stop = True
                task.status = TaskStatus.STOPPED
            return True
        return False


# Global singleton instance
task_manager = TaskManager()
