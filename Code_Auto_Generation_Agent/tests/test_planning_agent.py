"""测试 PlanningAgent 工具函数"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.agents.planning_agent import (
    _create_add_task,
    _create_finish,
    _create_validate_task_graph,
)


@pytest.fixture
def task_graph_validator():
    return {"tasks": []}


class TestAddTaskTool:
    """测试 add_task 工具"""

    def test_add_single_task(self, task_graph_validator):
        """添加单个任务"""
        add_task = _create_add_task(task_graph_validator)
        result = add_task.invoke({
            "task_id": "T001",
            "title": "初始化项目",
            "description": "创建项目结构",
            "task_type": "infrastructure",
        })

        assert "已添加任务" in result
        assert "T001" in result
        assert "初始化项目" in result
        assert len(task_graph_validator["tasks"]) == 1
        assert task_graph_validator["tasks"][0]["id"] == "T001"
        assert task_graph_validator["tasks"][0]["type"] == "infrastructure"

    def test_add_task_with_dependencies(self, task_graph_validator):
        """添加带依赖的任务"""
        # 先添加一个被依赖的任务
        task_graph_validator["tasks"].append({
            "id": "T001",
            "title": "Task 1",
            "dependencies": [],
        })

        add_task = _create_add_task(task_graph_validator)
        result = add_task.invoke({
            "task_id": "T002",
            "title": "Task 2",
            "description": "Depends on T001",
            "dependencies": ["T001"],
        })

        assert "已添加任务" in result
        assert len(task_graph_validator["tasks"]) == 2
        assert task_graph_validator["tasks"][1]["dependencies"] == ["T001"]

    def test_add_task_default_dependencies_omitted(self, task_graph_validator):
        """省略 dependencies 时默认为空列表"""
        add_task = _create_add_task(task_graph_validator)
        add_task.invoke({
            "task_id": "T001",
            "title": "Test",
            "description": "Test",
        })

        assert task_graph_validator["tasks"][0]["dependencies"] == []

    def test_add_task_default_dependencies_omitted(self, task_graph_validator):
        """省略 dependencies 参数时默认为空列表"""
        add_task = _create_add_task(task_graph_validator)
        add_task.invoke({
            "task_id": "T001",
            "title": "Test",
            "description": "Test",
        })

        assert task_graph_validator["tasks"][0]["dependencies"] == []

    def test_add_task_duplicate_id_rejected(self, task_graph_validator):
        """重复的任务 ID 被拒绝"""
        # 先添加 T001
        task_graph_validator["tasks"].append({"id": "T001", "title": "Existing Task"})

        add_task = _create_add_task(task_graph_validator)
        result = add_task.invoke({
            "task_id": "T001",
            "title": "Duplicate Task",
            "description": "Should be rejected",
        })

        assert "任务 ID 已存在" in result
        assert len(task_graph_validator["tasks"]) == 1  # 没有新增

    def test_add_task_default_type(self, task_graph_validator):
        """默认任务类型是 'general'"""
        add_task = _create_add_task(task_graph_validator)
        add_task.invoke({
            "task_id": "T001",
            "title": "Test",
            "description": "Test",
        })

        assert task_graph_validator["tasks"][0]["type"] == "general"


class TestValidateTaskGraphTool:
    """测试 validate_task_graph 工具"""

    def test_validate_empty_graph(self, task_graph_validator):
        """空任务图"""
        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "验证通过" in result
        assert task_graph_validator["validated"] is True

    def test_validate_single_task_no_deps(self, task_graph_validator):
        """单个无依赖任务"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": []}
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "验证通过" in result
        assert task_graph_validator["validated"] is True

    def test_validate_linear_dependencies(self, task_graph_validator):
        """线性依赖 T001 → T002"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": []},
            {"id": "T002", "title": "Task 2", "dependencies": ["T001"]},
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "验证通过" in result

    def test_validate_duplicate_ids(self, task_graph_validator):
        """重复的任务 ID"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": []},
            {"id": "T001", "title": "Task 2", "dependencies": []},  # 重复
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "任务 ID 重复" in result
        assert "T001" in result
        assert "validated" not in task_graph_validator  # 未设置

    def test_validate_nonexistent_dependency(self, task_graph_validator):
        """依赖不存在的任务"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": ["T999"]},
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "依赖不存在的任务" in result
        assert "T999" in result

    def test_validate_cyclic_dependency_direct(self, task_graph_validator):
        """直接循环依赖：T001 → T002 → T001"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": ["T002"]},
            {"id": "T002", "title": "Task 2", "dependencies": ["T001"]},
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "循环依赖" in result

    def test_validate_self_cyclic_dependency(self, task_graph_validator):
        """自依赖：T001 → T001"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": ["T001"]},
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "循环依赖" in result

    def test_validate_complex_diamond_graph(self, task_graph_validator):
        """菱形依赖：T001 是 T002、T003 的前置，T002、T003 是 T004 的前置"""
        task_graph_validator["tasks"] = [
            {"id": "T001", "title": "Task 1", "dependencies": []},
            {"id": "T002", "title": "Task 2", "dependencies": ["T001"]},
            {"id": "T003", "title": "Task 3", "dependencies": ["T001"]},
            {"id": "T004", "title": "Task 4", "dependencies": ["T002", "T003"]},
        ]

        validate = _create_validate_task_graph(task_graph_validator)
        result = validate.invoke({})

        assert "验证通过" in result


class TestFinishTool:
    """测试 finish 工具"""

    def test_finish_after_validation(self, task_graph_validator):
        """验证通过后可以正常完成"""
        task_graph_validator["validated"] = True

        finish = _create_finish(task_graph_validator)
        result = finish.invoke({"summary": "All tasks planned!"})

        assert "任务规划完成" in result
        assert "All tasks planned!" in result

    def test_finish_before_validation_rejected(self, task_graph_validator):
        """未验证就调用 finish 被拒绝"""
        # validated 未设置
        finish = _create_finish(task_graph_validator)
        result = finish.invoke({"summary": "Premature finish"})

        assert "必须先调用 validate_task_graph" in result

    def test_finish_validation_set_to_false(self, task_graph_validator):
        """validated = False 也被拒绝"""
        task_graph_validator["validated"] = False

        finish = _create_finish(task_graph_validator)
        result = finish.invoke({"summary": "Premature finish"})

        assert "必须先调用 validate_task_graph" in result


class TestPlanningAgentIntegration:
    """PlanningAgent 集成测试"""

    def test_planning_agent_init_tools(self):
        """测试 Agent 初始化时工具创建"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None

        agent = PlanningAgent(mock_llm, "/tmp/test", mock_config)

        # 应该有 7 个工具（4 个基类工具 + 3 个子类工具）
        assert len(agent.tools) == 7
        tool_names = [t.name for t in agent.tools]
        assert "add_task" in tool_names
        assert "validate_task_graph" in tool_names
        assert "finish" in tool_names

    def test_planning_agent_get_task_graph(self):
        """测试获取任务图"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None

        agent = PlanningAgent(mock_llm, "/tmp/test", mock_config)

        # 初始状态为空
        assert agent.get_task_graph() == []

    def test_planning_agent_run_and_parse(self):
        """测试 run_and_parse 方法"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None
        mock_config.max_iterations = 10

        agent = PlanningAgent(mock_llm, "/tmp/test", mock_config)

        # Mock prompt_loader 和 run
        with patch.object(agent.prompt_loader, "load") as mock_load:
            mock_template = MagicMock()
            mock_template.render.return_value = "plan this"
            mock_load.return_value = mock_template

            with patch.object(agent, "run") as mock_run:
                # 模拟任务被添加
                agent._task_graph_ref["tasks"] = [
                    {"id": "T001", "title": "Task 1"},
                    {"id": "T002", "title": "Task 2"},
                ]

                result = agent.run_and_parse("PRD content", "Arch content", verbose=False)

        assert len(result) == 2
        assert result[0]["id"] == "T001"
        assert result[1]["id"] == "T002"
        mock_run.assert_called_once()
