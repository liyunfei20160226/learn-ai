"""
单元测试: pipeline_graph.py 各个顶层函数
按照函数逐个测试，保证每个函数内代码全覆盖
"""
from unittest.mock import Mock
from se_pipeline.graph.pipeline_graph import (
    analyst_node, verifier_node, final_node, wait_user_node, quality_gate_node,
    after_analyst, after_verifier, after_quality_gate,
    build_requirements_internal_graph, create_requirements_internal_app
)
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.agents import RequirementsAnalystAgent, RequirementsVerifierAgent
from se_pipeline.quality_gate import AutoReviewer


class TestAnalystNode:
    """测试 analyst_node 函数"""

    def test_analyst_node_calls_analyst_run_and_returns_result(self):
        """测试 analyst_node 正确调用 analyst.run 并返回结果
        覆盖函数内所有代码（只有一行）
        """
        # 准备 mock
        mock_analyst = Mock(spec=RequirementsAnalystAgent)
        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )
        expected_result = mock_state.model_copy()
        expected_result.needs_more_questions = True
        mock_analyst.run.return_value = expected_result

        # 执行
        result = analyst_node(mock_state, mock_analyst)

        # 验证
        mock_analyst.run.assert_called_once_with(mock_state)
        assert result is expected_result


class TestVerifierNode:
    """测试 verifier_node 函数"""

    def test_verifier_node_calls_verifier_run_and_returns_result(self):
        """测试 verifier_node 正确调用 verifier.run 并返回结果
        覆盖函数内所有代码（只有一行）
        """
        # 准备 mock
        mock_verifier = Mock(spec=RequirementsVerifierAgent)
        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "问题", "answer": "回答"}
            ]
        )
        expected_result = mock_state.model_copy()
        expected_result.needs_more_questions = False
        mock_verifier.run.return_value = expected_result

        # 执行
        result = verifier_node(mock_state, mock_verifier)

        # 验证
        mock_verifier.run.assert_called_once_with(mock_state)
        assert result is expected_result


class TestFinalNode:
    """测试 final_node 函数"""

    def test_final_node_calls_finalizer_run_and_returns_result(self):
        """测试 final_node 正确调用 finalizer.run 并返回结果
        覆盖函数内所有代码（只有一行）
        """
        # 准备 mock
        from se_pipeline.agents import RequirementsFinalAgent
        mock_finalizer = Mock(spec=RequirementsFinalAgent)
        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "问题1", "answer": "回答1"},
                {"question": "问题2", "answer": "回答2"}
            ],
            needs_more_questions=False
        )
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        expected_result = mock_state.model_copy()
        expected_result.requirements_spec = RequirementsSpec(
            stage_id="requirements", project_id="test-001", data=spec_data
        )
        mock_finalizer.run.return_value = expected_result

        # 执行
        result = final_node(mock_state, mock_finalizer)

        # 验证
        mock_finalizer.run.assert_called_once_with(mock_state)
        assert result is expected_result


class TestWaitUserNode:
    """测试 wait_user_node 函数"""

    def test_wait_user_node_returns_state_unchanged(self):
        """测试 wait_user_node 直接返回原状态，不做任何修改
        覆盖函数内所有代码
        """
        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )

        # 执行
        result = wait_user_node(mock_state)

        # 验证：返回同一个对象，没有修改
        assert result is mock_state


class TestQualityGateNode:
    """测试 quality_gate_node 函数"""

    def test_quality_gate_node_when_spec_is_none_does_nothing(self):
        """测试 requirements_spec 为 None 时不做任何操作
        覆盖分支 if state.requirements_spec is not None:
        """
        mock_reviewer = Mock(spec=AutoReviewer)
        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=None,
            requirements_verification_passed=True,
            needs_more_questions=False
        )
        original_verification = mock_state.requirements_verification_passed
        original_needs = mock_state.needs_more_questions

        # 执行
        result = quality_gate_node(mock_state, mock_reviewer)

        # 验证：状态未改变
        assert result.requirements_verification_passed == original_verification
        assert result.needs_more_questions == original_needs
        mock_reviewer.review_requirements.assert_not_called()

    def test_quality_gate_node_when_review_failed_updates_state(self):
        """测试评审不通过时更新状态为需要回流
        覆盖分支 if not result.passed:
        """
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        spec = RequirementsSpec(stage_id="requirements", project_id="test-001", data=spec_data)

        mock_reviewer = Mock(spec=AutoReviewer)
        mock_result = Mock()
        mock_result.passed = False
        mock_reviewer.review_requirements.return_value = mock_result

        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=spec,
            requirements_verification_passed=True,
            needs_more_questions=False
        )

        # 执行
        result = quality_gate_node(mock_state, mock_reviewer)

        # 验证：状态已更新
        assert result.requirements_verification_passed is False
        assert result.needs_more_questions is True
        mock_reviewer.review_requirements.assert_called_once_with(spec)

    def test_quality_gate_node_when_review_passed_keeps_state(self):
        """测试评审通过时不改变状态
        覆盖 else 路径（不进入 if not result.passed）
        """
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        spec = RequirementsSpec(stage_id="requirements", project_id="test-001", data=spec_data)

        mock_reviewer = Mock(spec=AutoReviewer)
        mock_result = Mock()
        mock_result.passed = True
        mock_reviewer.review_requirements.return_value = mock_result

        mock_state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=spec,
            requirements_verification_passed=True,
            needs_more_questions=False
        )
        original_verification = mock_state.requirements_verification_passed
        original_needs = mock_state.needs_more_questions

        # 执行
        result = quality_gate_node(mock_state, mock_reviewer)

        # 验证：状态保持不变
        assert result.requirements_verification_passed == original_verification
        assert result.needs_more_questions == original_needs
        mock_reviewer.review_requirements.assert_called_once_with(spec)


class TestAfterAnalyst:
    """测试 after_analyst 条件路由函数"""

    def test_after_analyst_with_unanswered_questions_goes_to_wait_user(self):
        """有未回答问题时路由到 wait_user"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "问题1", "answer": "回答1"},
                {"question": "问题2", "answer": None},
            ]
        )
        result = after_analyst(state)
        assert result == "wait_user"

    def test_after_analyst_all_answered_goes_to_verifier(self):
        """所有问题都已回答时路由到 verifier"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "问题1", "answer": "回答1"},
                {"question": "问题2", "answer": "回答2"},
            ]
        )
        result = after_analyst(state)
        assert result == "verifier"

    def test_after_analyst_empty_history_goes_to_verifier(self):
        """空问答历史时路由到 verifier"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[]
        )
        result = after_analyst(state)
        assert result == "verifier"


class TestAfterVerifier:
    """测试 after_verifier 条件路由函数"""

    def test_after_verifier_needs_more_questions_goes_to_analyst(self):
        """需要更多问题时回流到 analyst"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            needs_more_questions=True
        )
        result = after_verifier(state)
        assert result == "analyst"

    def test_after_verifier_no_more_questions_goes_to_final(self):
        """不需要更多问题时进入 final"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            needs_more_questions=False
        )
        result = after_verifier(state)
        assert result == "final"


class TestAfterQualityGate:
    """测试 after_quality_gate 条件路由函数"""

    def test_after_quality_gate_all_conditions_met_goes_to_end(self):
        """所有条件都满足时结束到 __end__"""
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        spec = RequirementsSpec(stage_id="requirements", project_id="test-001", data=spec_data)
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=spec,
            requirements_verification_passed=True,
            needs_more_questions=False
        )
        result = after_quality_gate(state)
        assert result == "__end__"

    def test_after_quality_gate_spec_none_goes_to_analyst(self):
        """spec 为 None 时回流到 analyst"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=None,
            requirements_verification_passed=True,
            needs_more_questions=False
        )
        result = after_quality_gate(state)
        assert result == "analyst"

    def test_after_quality_gate_verification_failed_goes_to_analyst(self):
        """验证不通过时回流到 analyst"""
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        spec = RequirementsSpec(stage_id="requirements", project_id="test-001", data=spec_data)
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=spec,
            requirements_verification_passed=False,
            needs_more_questions=False
        )
        result = after_quality_gate(state)
        assert result == "analyst"

    def test_after_quality_gate_needs_more_questions_goes_to_analyst(self):
        """仍需要提问时回流到 analyst"""
        from se_pipeline.types.artifacts import RequirementsSpec
        spec_data = RequirementsSpec.RequirementsData(
            title="测试", description="测试", functional_requirements=[], non_functional_requirements=[]
        )
        spec = RequirementsSpec(stage_id="requirements", project_id="test-001", data=spec_data)
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_spec=spec,
            requirements_verification_passed=True,
            needs_more_questions=True
        )
        result = after_quality_gate(state)
        assert result == "analyst"


class TestBuildRequirementsInternalGraph:
    """测试 build_requirements_internal_graph 构建函数"""

    def test_build_creates_state_graph_with_all_nodes(self):
        """测试构建返回正确的StateGraph，包含所有预期节点"""
        from langgraph.graph import StateGraph
        from langchain_openai import ChatOpenAI
        mock_llm = Mock(spec=ChatOpenAI)

        from se_pipeline.agents import (
            RequirementsAnalystAgent, RequirementsVerifierAgent,
            RequirementsFinalAgent
        )
        from se_pipeline.quality_gate import AutoReviewer

        # 直接测试构建过程，覆盖所有代码行
        from unittest.mock import patch
        with patch('se_pipeline.graph.pipeline_graph.RequirementsAnalystAgent') as mock_a, \
             patch('se_pipeline.graph.pipeline_graph.RequirementsVerifierAgent') as mock_v, \
             patch('se_pipeline.graph.pipeline_graph.RequirementsFinalAgent') as mock_f, \
             patch('se_pipeline.graph.pipeline_graph.AutoReviewer') as mock_r:
            mock_a.return_value = Mock(spec=RequirementsAnalystAgent)
            mock_v.return_value = Mock(spec=RequirementsVerifierAgent)
            mock_f.return_value = Mock(spec=RequirementsFinalAgent)
            mock_r.return_value = Mock(spec=AutoReviewer)

            graph = build_requirements_internal_graph(mock_llm)

            # 验证返回类型正确
            assert isinstance(graph, StateGraph)

            # 验证所有节点都已添加
            assert "analyst" in graph.nodes
            assert "wait_user" in graph.nodes
            assert "verifier" in graph.nodes
            assert "final" in graph.nodes
            assert "quality_gate" in graph.nodes

            # 验证Agents都被初始化
            mock_a.assert_called_once_with(mock_llm)
            mock_v.assert_called_once_with(mock_llm)
            mock_f.assert_called_once_with(mock_llm)
            mock_r.assert_called_once_with(mock_llm)


class TestCreateRequirementsInternalApp:
    """测试 create_requirements_internal_app 创建应用函数"""

    def test_create_returns_compiled_graph(self):
        """测试创建编译后的可执行图"""
        from langchain_openai import ChatOpenAI
        mock_llm = Mock(spec=ChatOpenAI)

        from unittest.mock import patch
        from se_pipeline.agents import (
            RequirementsAnalystAgent, RequirementsVerifierAgent,
            RequirementsFinalAgent
        )
        from se_pipeline.quality_gate import AutoReviewer

        with patch('se_pipeline.graph.pipeline_graph.RequirementsAnalystAgent') as mock_a, \
             patch('se_pipeline.graph.pipeline_graph.RequirementsVerifierAgent') as mock_v, \
             patch('se_pipeline.graph.pipeline_graph.RequirementsFinalAgent') as mock_f, \
             patch('se_pipeline.graph.pipeline_graph.AutoReviewer') as mock_r:
            mock_a.return_value = Mock(spec=RequirementsAnalystAgent)
            mock_v.return_value = Mock(spec=RequirementsVerifierAgent)
            mock_f.return_value = Mock(spec=RequirementsFinalAgent)
            mock_r.return_value = Mock(spec=AutoReviewer)

            app = create_requirements_internal_app(mock_llm)

            # 验证编译后的图有invoke方法
            assert hasattr(app, "invoke")
            assert callable(app.invoke)
