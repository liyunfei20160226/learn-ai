"""测试代码生成协调器"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.coordinator import CodegenCoordinator
from core.manifest import TaskState


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.openai_api_key = "test-key"
    config.openai_base_url = None
    config.openai_model = "gpt-4"
    config.openai_temperature = 0.0
    config.openai_timeout = 120
    config.openai_max_retries = 3
    config.working_dir = None
    config.prompts_dir = None
    return config


class TestTopologicalSort:
    """测试拓扑排序"""

    def test_simple_linear_dependencies(self, temp_dir, mock_config):
        """简单线性依赖：A → B → C"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=[])
        task_b = TaskState(id="B", name="Task B", dependencies=["A"])
        task_c = TaskState(id="C", name="Task C", dependencies=["B"])

        sorted_tasks = coordinator._topological_sort([task_a, task_b, task_c])

        assert [t.id for t in sorted_tasks] == ["A", "B", "C"]

    def test_multiple_independent_tasks(self, temp_dir, mock_config):
        """多个独立任务，无依赖"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=[])
        task_b = TaskState(id="B", name="Task B", dependencies=[])
        task_c = TaskState(id="C", name="Task C", dependencies=[])

        sorted_tasks = coordinator._topological_sort([task_a, task_b, task_c])

        # 无依赖的任务顺序不保证，但都应该在结果中
        assert set(t.id for t in sorted_tasks) == {"A", "B", "C"}

    def test_diamond_dependencies(self, temp_dir, mock_config):
        """菱形依赖：A 是 B 和 C 的前置，B、C 是 D 的前置"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=[])
        task_b = TaskState(id="B", name="Task B", dependencies=["A"])
        task_c = TaskState(id="C", name="Task C", dependencies=["A"])
        task_d = TaskState(id="D", name="Task D", dependencies=["B", "C"])

        sorted_tasks = coordinator._topological_sort([task_a, task_b, task_c, task_d])

        sorted_ids = [t.id for t in sorted_tasks]
        assert sorted_ids.index("A") < sorted_ids.index("B")
        assert sorted_ids.index("A") < sorted_ids.index("C")
        assert sorted_ids.index("B") < sorted_ids.index("D")
        assert sorted_ids.index("C") < sorted_ids.index("D")

    def test_nonexistent_dependency_raises(self, temp_dir, mock_config):
        """依赖不存在的任务 ID 应该抛出异常"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=["NOT_EXIST"])

        with pytest.raises(ValueError, match="依赖不存在的任务"):
            coordinator._topological_sort([task_a])

    def test_cyclic_dependency_raises(self, temp_dir, mock_config):
        """循环依赖应该抛出异常：A → B → C → A"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=["C"])
        task_b = TaskState(id="B", name="Task B", dependencies=["A"])
        task_c = TaskState(id="C", name="Task C", dependencies=["B"])

        with pytest.raises(ValueError, match="循环依赖"):
            coordinator._topological_sort([task_a, task_b, task_c])

    def test_self_cyclic_dependency_raises(self, temp_dir, mock_config):
        """自依赖：A 依赖 A"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        task_a = TaskState(id="A", name="Task A", dependencies=["A"])

        with pytest.raises(ValueError, match="循环依赖"):
            coordinator._topological_sort([task_a])

    def test_empty_task_list(self, temp_dir, mock_config):
        """空任务列表"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        sorted_tasks = coordinator._topological_sort([])
        assert sorted_tasks == []


class TestRequireField:
    """测试 _require_field 字段检查"""

    def test_require_field_exists(self, temp_dir, mock_config):
        """字段存在时返回值"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        data = {"framework": "FastAPI"}
        result = coordinator._require_field(data, "framework", "backend")
        assert result == "FastAPI"

    def test_require_field_missing_raises(self, temp_dir, mock_config):
        """字段缺失时抛出异常"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        data = {"framework": "FastAPI"}

        with pytest.raises(ValueError, match="架构文档缺少必填字段"):
            coordinator._require_field(data, "database", "backend")

    def test_require_field_none_data_raises(self, temp_dir, mock_config):
        """data 为 None 时抛出异常"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        with pytest.raises(ValueError, match="架构文档缺少必填字段"):
            coordinator._require_field(None, "framework", "backend")


class TestFilterArchitectureDocs:
    """测试架构文档过滤"""

    @pytest.fixture
    def sample_arch(self):
        return {
            "backend": {
                "framework": "FastAPI",
                "database": "PostgreSQL",
                "orm": "SQLAlchemy",
                "migration": "Alembic",
                "directory_structure": "src/db/\nsrc/api/",
            },
            "frontend": {
                "framework": "React",
                "state_management": "Redux",
                "ui_library": "Ant Design",
                "directory_structure": "src/components/\nsrc/pages/",
            },
        }

    def test_filter_backend(self, temp_dir, mock_config, sample_arch):
        """过滤后端任务类型"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._filter_architecture_docs("backend", sample_arch)

        assert "后端技术栈" in result
        assert "FastAPI" in result
        assert "PostgreSQL" in result
        assert "SQLAlchemy" in result

    def test_filter_frontend(self, temp_dir, mock_config, sample_arch):
        """过滤前端任务类型"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._filter_architecture_docs("frontend", sample_arch)

        assert "前端技术栈" in result
        assert "React" in result
        assert "Redux" in result
        assert "Ant Design" in result

    def test_filter_database(self, temp_dir, mock_config, sample_arch):
        """过滤数据库任务类型"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._filter_architecture_docs("database", sample_arch)

        assert "数据库技术栈" in result
        assert "PostgreSQL" in result
        assert "Alembic" in result

    def test_filter_shared(self, temp_dir, mock_config, sample_arch):
        """过滤 shared 任务类型（前后端都包含）"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._filter_architecture_docs("shared", sample_arch)

        assert "后端技术栈" in result
        assert "前端技术栈" in result
        assert "FastAPI" in result
        assert "React" in result

    def test_filter_backend_missing_field_raises(self, temp_dir, mock_config, sample_arch):
        """后端字段缺失时抛出异常"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        del sample_arch["backend"]["orm"]

        with pytest.raises(ValueError, match="架构文档缺少必填字段"):
            coordinator._filter_architecture_docs("backend", sample_arch)

    def test_filter_frontend_missing_field_raises(self, temp_dir, mock_config, sample_arch):
        """前端字段缺失时抛出异常"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        del sample_arch["frontend"]["ui_library"]

        with pytest.raises(ValueError, match="架构文档缺少必填字段"):
            coordinator._filter_architecture_docs("frontend", sample_arch)


class TestCollectDependencyCode:
    """测试依赖代码收集"""

    def test_no_dependencies_returns_empty(self, temp_dir, mock_config):
        """无依赖时返回空字符串"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._collect_dependency_code([])
        assert result == ""

    def test_dependency_not_in_cache(self, temp_dir, mock_config):
        """依赖任务不在缓存中时返回警告"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        result = coordinator._collect_dependency_code(["task_not_exist"])

        assert "未完成，代码不可用" in result

    def test_dependency_in_cache_but_file_not_exist(self, temp_dir, mock_config):
        """依赖在缓存中但文件不存在时"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)
        coordinator.generated_code_cache["task_1"] = [{"file_path": "not_exist.py"}]

        result = coordinator._collect_dependency_code(["task_1"])

        assert "任务 task_1 已生成代码" in result

    def test_dependency_in_cache_with_existing_file(self, temp_dir, mock_config):
        """依赖在缓存中且文件存在时，读取文件内容"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        # 创建测试文件
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        coordinator.generated_code_cache["task_1"] = [{"file_path": "test.py"}]

        result = coordinator._collect_dependency_code(["task_1"])

        assert "任务 task_1 已生成代码" in result
        assert "test.py" in result
        assert "print('hello')" in result

    def test_lru_cache_move_to_end(self, temp_dir, mock_config):
        """测试 LRU：访问元素后移到末尾"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        # 预填充缓存
        coordinator.generated_code_cache["task_1"] = []
        coordinator.generated_code_cache["task_2"] = []
        coordinator.generated_code_cache["task_3"] = []

        # 初始顺序：task_1 → task_2 → task_3
        assert list(coordinator.generated_code_cache.keys()) == ["task_1", "task_2", "task_3"]

        # 访问 task_1
        coordinator._collect_dependency_code(["task_1"])

        # 访问后顺序：task_2 → task_3 → task_1 (task_1 移到最后)
        assert list(coordinator.generated_code_cache.keys()) == ["task_2", "task_3", "task_1"]


class TestCoordinatorInit:
    """测试 Coordinator 初始化"""

    def test_coordinator_basic_init(self, temp_dir, mock_config):
        """基本初始化"""
        coordinator = CodegenCoordinator(working_dir=temp_dir, config=mock_config)

        assert coordinator.working_dir == temp_dir.resolve()
        assert coordinator.config == mock_config
        assert coordinator.manifest is None
        assert coordinator.generated_code_cache == {}

    def test_coordinator_api_key_priority(self, temp_dir, mock_config):
        """参数优先级高于配置"""
        coordinator = CodegenCoordinator(
            api_key="override-key",
            working_dir=temp_dir,
            config=mock_config,
        )
        assert coordinator.api_key == "override-key"

    def test_coordinator_working_dir_created(self, temp_dir, mock_config):
        """工作目录不存在时自动创建"""
        new_dir = temp_dir / "new_subdir"
        assert not new_dir.exists()

        CodegenCoordinator(working_dir=new_dir, config=mock_config)

        assert new_dir.exists()
