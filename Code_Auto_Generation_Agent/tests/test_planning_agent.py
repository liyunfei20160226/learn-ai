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
    # module_id 现在通过字典的 _module_id 字段传递，而不是工厂参数
    return {"tasks": [], "id_mapping": {}, "_module_id": "B-MOD-001"}


class TestAddTaskTool:
    """测试 add_task 工具（内置 ID 自动转换）"""

    def test_add_single_task(self, task_graph_validator):
        """添加单个任务 - 验证 ID 被自动转换为 {module_id}_{序号} 格式"""
        add_task = _create_add_task(task_graph_validator)  # module_id 通过字典的 _module_id 字段传递
        result = add_task.invoke({
            "task_id": "T001",  # LLM 传什么都无所谓
            "title": "初始化项目",
            "description": "创建项目结构",
            "task_type": "infrastructure",
        })

        assert "已添加任务" in result
        assert "B-MOD-001_01" in result  # 验证输出显示真实 ID
        assert "初始化项目" in result
        assert len(task_graph_validator["tasks"]) == 1
        assert task_graph_validator["tasks"][0]["id"] == "B-MOD-001_01"  # 真实 ID
        assert task_graph_validator["tasks"][0]["type"] == "infrastructure"
        # 验证映射表正确
        assert task_graph_validator["id_mapping"]["T001"] == "B-MOD-001_01"

    def test_add_task_with_dependencies(self, task_graph_validator):
        """添加带依赖的任务 - 验证 dependencies 中的 ID 也被自动转换"""
        # 先添加一个被依赖的任务（通过工具正常添加，这样 id_mapping 会被正确填充）
        add_task = _create_add_task(task_graph_validator)
        add_task.invoke({
            "task_id": "T001",
            "title": "Task 1",
            "description": "Task 1",
            "dependencies": [],
        })

        # 添加第二个任务，依赖 T001
        result = add_task.invoke({
            "task_id": "T002",
            "title": "Task 2",
            "description": "Depends on T001",
            "dependencies": ["T001"],
        })

        assert "已添加任务" in result
        assert "B-MOD-001_02" in result
        assert len(task_graph_validator["tasks"]) == 2
        # 关键：依赖 ID T001 被自动转换为 B-MOD-001_01
        assert task_graph_validator["tasks"][1]["dependencies"] == ["B-MOD-001_01"]

    def test_add_task_cross_module_no_conflict(self, task_graph_validator):
        """验证不同模块用相同的 LLM ID 不会冲突"""
        # 模块 1 添加 T001
        add_task_1 = _create_add_task({"tasks": [], "id_mapping": {}, "_module_id": "B-MOD-001"})
        add_task_1.invoke({"task_id": "T001", "title": "模块1任务", "description": "模块1任务"})

        # 模块 2 添加 T001（同一个 LLM ID，不同模块）
        task_graph_2 = {"tasks": [], "id_mapping": {}, "_module_id": "B-MOD-002"}
        add_task_2 = _create_add_task(task_graph_2)
        result = add_task_2.invoke({"task_id": "T001", "title": "模块2任务", "description": "模块2任务"})

        # 不会报错，ID 被正确转换为各自的模块前缀
        assert "B-MOD-002_01" in result
        assert len(task_graph_2["tasks"]) == 1
        assert task_graph_2["tasks"][0]["id"] == "B-MOD-002_01"

    def test_add_task_default_dependencies_omitted(self, task_graph_validator):
        """省略 dependencies 参数时默认为空列表"""
        add_task = _create_add_task(task_graph_validator)
        add_task.invoke({
            "task_id": "T001",
            "title": "Test",
            "description": "Test",
        })

        assert task_graph_validator["tasks"][0]["dependencies"] == []

    def test_add_task_no_duplicate_error_anymore(self, task_graph_validator):
        """验证：重复的 LLM ID 不再报错，因为我们会自动重编号"""
        # 现在即使 LLM 重复调用 add_task(T001)，也不会报错，因为我们按顺序编号
        add_task = _create_add_task(task_graph_validator)
        result1 = add_task.invoke({
            "task_id": "T001",  # LLM 第一次用 T001
            "title": "Task 1",
            "description": "First",
        })
        assert "B-MOD-001_01" in result1

        result2 = add_task.invoke({
            "task_id": "T001",  # LLM 傻了，又用 T001
            "title": "Task 2",
            "description": "Second",
        })
        assert "B-MOD-001_02" in result2  # 自动转成 02，不报错

        assert len(task_graph_validator["tasks"]) == 2  # 两个任务都添加成功

    def test_dependency_id_format_normalization(self, task_graph_validator):
        """验证：依赖 ID 多种格式都能被正确转换（LLM 格式不统一问题）"""
        add_task = _create_add_task(task_graph_validator)

        # 添加前 6 个任务，LLM 使用 T 前缀格式
        for i in range(1, 7):
            add_task.invoke({
                "task_id": f"T{i:03d}",
                "title": f"任务 {i}",
                "description": f"任务 {i} 描述",
                "dependencies": [],
            })

        # 添加第 7 个任务，依赖用纯数字格式（如 "06"）- 这是 LLM 实际会生成的
        result = add_task.invoke({
            "task_id": "T007",
            "title": "任务 7",
            "description": "依赖任务 6",
            "dependencies": ["06"],  # LLM 传纯数字，而不是 T006
        })

        # 验证：纯数字 "06" 被正确转换为 B-MOD-001_06
        assert task_graph_validator["tasks"][6]["dependencies"] == ["B-MOD-001_06"]

        # 添加第 8 个任务，依赖混合多种格式
        result = add_task.invoke({
            "task_id": "T008",
            "title": "任务 8",
            "description": "依赖多个任务，格式不统一",
            "dependencies": [
                "05",       # 纯数字格式
                "T006",     # 标准 T 前缀格式
                "B-MOD-001_07",  # 带模块前缀格式（LLM 可能学到这种格式）
            ],
        })

        # 验证：三种格式都被正确转换
        deps = set(task_graph_validator["tasks"][7]["dependencies"])
        assert deps == {"B-MOD-001_05", "B-MOD-001_06", "B-MOD-001_07"}

    def test_module_id_switch_in_place(self):
        """验证：通过原地修改 _module_id 可以切换模块（核心测试！）"""
        # 创建一个共享字典，模拟 agent 的 self._task_graph_ref
        shared_state = {"tasks": [], "id_mapping": {}, "_module_id": "B-MOD-001"}

        add_task = _create_add_task(shared_state)

        # 第一个模块添加任务
        result1 = add_task.invoke({
            "task_id": "T001",
            "title": "任务1",
            "description": "d1",
        })
        assert "B-MOD-001_01" in result1

        # 切换模块（原地修改 _module_id，不重新创建工具！）
        shared_state.clear()
        shared_state["tasks"] = []
        shared_state["id_mapping"] = {}
        shared_state["validated"] = False
        shared_state["_module_id"] = "B-MOD-002"

        # 第二个模块添加任务，同一个工具，同一个 shared_state 引用
        result2 = add_task.invoke({
            "task_id": "T001",  # LLM 还是用 T001，但因为切换了 module_id
            "title": "任务2",
            "description": "d2",
        })
        assert "B-MOD-002_01" in result2  # ✅ 自动使用新的 module_id！

        # 验证两个任务互不干扰
        assert shared_state["tasks"][0]["id"] == "B-MOD-002_01"

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

    def test_planning_agent_run_with_log(self):
        """测试 run_with_log 方法（Coordinator 实际调用的接口）"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None
        mock_config.max_iterations = 10

        agent = PlanningAgent(mock_llm, "/tmp/test", mock_config)

        # Mock prompt_loader
        with patch.object(agent.prompt_loader, "load") as mock_load:
            mock_template = MagicMock()
            mock_template.render.return_value = "plan this"
            mock_load.return_value = mock_template

            with patch.object(agent, "run") as mock_run:
                # 模拟 Agent.run 执行后任务被添加
                def side_effect(*args, **kwargs):
                    agent._task_graph_ref["tasks"] = [
                        {"id": "B-MOD-001_01", "title": "Task 1", "type": "backend", "dependencies": [], "_source_module_id": "B-MOD-001"},
                    ]
                    agent._task_graph_ref["validated"] = True
                mock_run.side_effect = side_effect

                # 构造最小可用的 PRD 和 架构 JSON
                prd_json = '{"userStories": [{"id": "US-001", "title": "Test", "acceptanceCriteria": []}]}'
                arch_json = '''{"backend": {"modules": [
                    {"id": "B-MOD-001", "name": "测试模块", "description": "测试", "directory": "app/test",
                     "userStoryIds": ["US-001"], "files": [], "dependencies": []}
                ]}}'''

                # 调用 Coordinator 实际使用的签名
                result = agent.run_with_log(prd_json, arch_json, verbose=False)

        assert len(result) == 1
        assert result[0]["id"] == "T001"
        assert result[0]["title"] == "Task 1"

    def test_planning_agent_run_and_parse(self):
        """测试 run_and_parse 方法（兼容旧接口）"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None
        mock_config.max_iterations = 10

        agent = PlanningAgent(mock_llm, "/tmp/test", mock_config)

        # Mock prompt_loader
        with patch.object(agent.prompt_loader, "load") as mock_load:
            mock_template = MagicMock()
            mock_template.render.return_value = "plan this"
            mock_load.return_value = mock_template

            with patch.object(agent, "run") as mock_run:
                def side_effect(*args, **kwargs):
                    agent._task_graph_ref["tasks"] = [
                        {"id": "B-MOD-001_01", "title": "Task 1", "type": "backend", "dependencies": [], "_source_module_id": "B-MOD-001"},
                    ]
                    agent._task_graph_ref["validated"] = True
                mock_run.side_effect = side_effect

                prd_json = '{"userStories": [{"id": "US-001", "title": "Test", "acceptanceCriteria": []}]}'
                arch_json = '''{"backend": {"modules": [
                    {"id": "B-MOD-001", "name": "测试模块", "description": "测试", "directory": "app/test",
                     "userStoryIds": ["US-001"], "files": [], "dependencies": []}
                ]}}'''

                result = agent.run_and_parse(prd_json, arch_json, verbose=False)

        assert len(result) == 1
        assert result[0]["id"] == "T001"


# ========== 新增：分阶段规划方法测试 ==========

class TestPlanningAgentStagedMethods:
    """测试分阶段规划的各个辅助方法"""

    def _create_agent(self):
        """创建测试用 PlanningAgent 实例"""
        from core.agents.planning_agent import PlanningAgent

        mock_llm = MagicMock()
        mock_config = MagicMock()
        mock_config.prompts_dir = None
        mock_config.max_iterations = 10

        return PlanningAgent(mock_llm, tempfile.mkdtemp(), mock_config)

    def test_clear_task_graph(self):
        """测试 _clear_task_graph 清空任务图"""
        agent = self._create_agent()
        agent._task_graph_ref["tasks"] = [{"id": "T001", "title": "Test"}]
        agent._task_graph_ref["validated"] = True

        agent._clear_task_graph()

        assert agent._task_graph_ref["tasks"] == []
        assert agent._task_graph_ref["validated"] is False

    def test_extract_stories_by_ids(self):
        """测试 _extract_stories_by_ids 根据 ID 提取 user story"""
        agent = self._create_agent()
        prd = {
            "userStories": [
                {"id": "US-001", "title": "Story 1"},
                {"id": "US-002", "title": "Story 2"},
                {"id": "US-003", "title": "Story 3"},
            ]
        }

        stories = agent._extract_stories_by_ids(prd, ["US-001", "US-003"])

        assert len(stories) == 2
        assert {s["id"] for s in stories} == {"US-001", "US-003"}

    def test_extract_arch_modules(self):
        """测试 _extract_arch_modules 从架构 JSON 直接提取模块"""
        agent = self._create_agent()

        arch_json = '''
        {
            "backend": {
                "modules": [
                    {"id": "B-MOD-001", "name": "核心配置", "description": "...", "directory": "app/core", "userStoryIds": ["US-001"]},
                    {"id": "B-MOD-002", "name": "数据模型", "description": "...", "directory": "app/models", "userStoryIds": ["US-001"]}
                ]
            },
            "frontend": {
                "modules": [
                    {"id": "F-MOD-001", "name": "主页面", "description": "...", "directory": "app/page", "userStoryIds": ["US-008"]}
                ]
            }
        }
        '''

        modules = agent._extract_arch_modules(arch_json)

        assert len(modules) == 3
        b_mods = [m for m in modules if m["type"] == "backend"]
        f_mods = [m for m in modules if m["type"] == "frontend"]
        assert len(b_mods) == 2
        assert len(f_mods) == 1
        assert b_mods[0]["module_id"] == "B-MOD-001"
        assert f_mods[0]["module_id"] == "F-MOD-001"

    def test_plan_single_module_tasks(self):
        """测试 _plan_single_module_tasks 规划单个模块任务"""
        agent = self._create_agent()
        module = {
            "module_id": "B-MOD-001",
            "name": "核心配置",
            "description": "核心配置模块",
            "directory": "app/core",
            "type": "backend",
            "files": [{"path": "app/core/config.py", "description": "配置文件"}],
        }
        stories = [{"id": "US-001", "title": "测试", "acceptanceCriteria": ["配置必须正确"]}]

        with patch.object(agent.prompt_loader, "load") as mock_load:
            mock_template = MagicMock()
            mock_template.render.return_value = "plan this"
            mock_load.return_value = mock_template

            with patch.object(agent, "run") as mock_run:
                def side_effect(*args, **kwargs):
                    agent._task_graph_ref["tasks"] = [
                        {"id": "B-MOD-001_01", "title": "创建配置文件", "type": "backend", "dependencies": []},
                    ]
                    agent._task_graph_ref["validated"] = True
                mock_run.side_effect = side_effect

                tasks = agent._plan_single_module_tasks(module, stories, verbose=False)

        assert len(tasks) == 1
        assert tasks[0]["id"] == "B-MOD-001_01"
        assert tasks[0]["_source_module_id"] == "B-MOD-001"

    def test_resolve_cross_module_deps(self):
        """测试 _resolve_cross_module_deps 跨模块依赖整理"""
        agent = self._create_agent()

        all_tasks = [
            {"id": "B-MOD-001_01", "title": "配置模块", "type": "backend", "dependencies": [], "_source_module_id": "B-MOD-001"},
            {"id": "B-MOD-002_01", "title": "数据模型", "type": "backend", "dependencies": [], "_source_module_id": "B-MOD-002"},
        ]
        arch_json = '''
        {
            "backend": {
                "modules": [
                    {"id": "B-MOD-001", "name": "核心配置", "dependencies": []},
                    {"id": "B-MOD-002", "name": "数据模型", "dependencies": ["B-MOD-001"]}
                ]
            }
        }
        '''

        result = agent._resolve_cross_module_deps(all_tasks, arch_json)

        # 应该统一重编号
        assert len(result) == 2
        assert result[0]["id"] == "T001"
        assert result[1]["id"] == "T002"
        # B-MOD-002 依赖 B-MOD-001，所以 T002 应该依赖 T001
        assert "T001" in result[1]["dependencies"]

        # 以上为完整测试
