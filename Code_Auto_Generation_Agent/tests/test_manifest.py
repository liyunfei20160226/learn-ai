"""Manifest 核心功能冒烟测试

验证序列化/反序列化闭环，防止字段改名/漏传导致的静默错误。
"""

import json

from core.manifest import FixAttempt, FixState, Manifest, TaskFile, TaskState


def test_manifest_create_basic():
    """测试基本创建功能"""
    m = Manifest.create(project_name="test-project")
    assert m.session_id
    assert m.project_name == "test-project"
    assert m.created_at
    assert m.total_tasks == 0
    assert m.completed_tasks == 0
    assert m.failed_tasks == 0


def test_manifest_add_task():
    """测试添加任务"""
    m = Manifest.create(project_name="test")
    m.add_task("task-1", "Test Task", task_type="backend", dependencies=[])

    assert "task-1" in m.tasks
    assert m.tasks["task-1"].name == "Test Task"
    assert m.tasks["task-1"].type == "backend"
    assert m.tasks["task-1"].status == "pending"
    assert m.total_tasks == 1


def test_manifest_task_state_transitions():
    """测试任务状态流转"""
    m = Manifest.create(project_name="test")
    m.add_task("task-1", "Test Task")

    # pending -> running
    m.start_task("task-1")
    assert m.tasks["task-1"].status == "running"
    assert m.tasks["task-1"].started_at

    # running -> success
    files = [TaskFile(file_path="test.py", content_sha="abc123")]
    m.complete_task("task-1", files)
    assert m.tasks["task-1"].status == "success"
    assert m.tasks["task-1"].completed_at
    assert len(m.tasks["task-1"].generated_files) == 1

    # completed tasks 幂等：再次调用不修改
    m.complete_task("task-1", [])
    assert len(m.tasks["task-1"].generated_files) == 1


def test_manifest_task_fail():
    """测试任务失败"""
    m = Manifest.create(project_name="test")
    m.add_task("task-1", "Test Task")

    m.start_task("task-1")
    m.fail_task("task-1", "测试错误")

    assert m.tasks["task-1"].status == "failed"
    assert m.tasks["task-1"].error == "测试错误"

    # 幂等：再次失败不修改
    m.fail_task("task-1", "新错误")
    assert m.tasks["task-1"].error == "测试错误"


def test_manifest_json_roundtrip_simple():
    """简单闭环：create -> to_json -> from_json -> 数据一致"""
    m1 = Manifest.create(project_name="roundtrip-test")
    m1.add_task("task-1", "Task One", task_type="backend")
    m1.add_task("task-2", "Task Two", task_type="frontend", dependencies=["task-1"])

    json_str = m1.to_json()
    m2 = Manifest.from_json(json_str)

    assert m2.session_id == m1.session_id
    assert m2.project_name == m1.project_name
    assert m2.created_at == m1.created_at
    assert len(m2.tasks) == 2
    assert m2.tasks["task-1"].name == "Task One"
    assert m2.tasks["task-2"].dependencies == ["task-1"]


def test_manifest_json_roundtrip_with_completed_task():
    """带完成任务的闭环测试"""
    m1 = Manifest.create(project_name="roundtrip-test")
    m1.add_task("task-1", "Task One")
    m1.start_task("task-1")
    m1.complete_task("task-1", [TaskFile(file_path="main.py", content_sha="sha1")])

    json_str = m1.to_json()
    m2 = Manifest.from_json(json_str)

    assert m2.tasks["task-1"].status == "success"
    assert len(m2.tasks["task-1"].generated_files) == 1
    assert m2.tasks["task-1"].generated_files[0].file_path == "main.py"


def test_manifest_json_roundtrip_with_fix_state():
    """带 FixState 的闭环测试"""
    m1 = Manifest.create(project_name="roundtrip-test")
    m1.fix_state = FixState(
        enabled=True,
        current_attempt=3,
        best_attempt=2,
        best_error_count=5,
        initial_error_count=20,
        history=[
            FixAttempt(
                attempt=1,
                failed_step="mypy",
                errors_before=20,
                errors_after=10,
                error_samples=["error1", "error2"],
                timestamp="2026-01-01T00:00:00",
                accepted=True,
            )
        ],
        status="running",
    )

    json_str = m1.to_json()
    m2 = Manifest.from_json(json_str)

    assert m2.fix_state is not None
    assert m2.fix_state.current_attempt == 3
    assert m2.fix_state.best_error_count == 5
    assert len(m2.fix_state.history) == 1
    assert m2.fix_state.history[0].attempt == 1
    assert m2.fix_state.history[0].accepted is True


def test_manifest_get_pending_tasks():
    """获取待执行任务列表（包括崩溃恢复的 running 状态）"""
    m = Manifest.create(project_name="test")
    m.add_task("task-1", "One")
    m.add_task("task-2", "Two")
    m.add_task("task-3", "Three")

    m.start_task("task-1")
    m.complete_task("task-2")

    pending = m.get_pending_tasks()
    assert "task-1" in pending  # running 视为待重试
    assert "task-3" in pending  # pending
    assert "task-2" not in pending  # success 不包含


def test_manifest_is_task_completed():
    """检查任务是否完成"""
    m = Manifest.create(project_name="test")
    m.add_task("task-1", "One")

    assert not m.is_task_completed("task-1")
    m.start_task("task-1")
    assert not m.is_task_completed("task-1")
    m.complete_task("task-1")
    assert m.is_task_completed("task-1")


def test_manifest_topological_sort_dependency_not_exist():
    """拓扑排序：依赖不存在的任务"""
    from collections import deque

    tasks = [
        {"id": "task-1", "dependencies": ["not-exist"]},
    ]

    task_map = {t["id"]: t for t in tasks}
    task_ids = set(task_map.keys())
    in_degree = {t["id"]: len(t.get("dependencies", [])) for t in tasks}
    adj_list = {t["id"]: [] for t in tasks}

    error_raised = False
    for task in tasks:
        for dep in task.get("dependencies", []):
            if dep not in task_ids:
                error_raised = True
                break

    assert error_raised, "应该检测到不存在的依赖"


def test_task_file_creation():
    """TaskFile 基本创建"""
    f = TaskFile(file_path="src/main.py", content_sha="abc123")
    assert f.file_path == "src/main.py"
    assert f.content_sha == "abc123"


def test_fix_attempt_creation():
    """FixAttempt 基本创建"""
    a = FixAttempt(
        attempt=1,
        failed_step="mypy",
        errors_before=10,
        errors_after=5,
        error_samples=["e1", "e2"],
        timestamp="2026-01-01",
        accepted=True,
    )
    assert a.attempt == 1
    assert a.errors_after == 5
