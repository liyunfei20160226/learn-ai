"""
单元测试: 需求验证官Agent RequirementsVerifierAgent
"""
import pytest
from unittest.mock import Mock, MagicMock
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_verifier import RequirementsVerifierAgent
from se_pipeline.types.pipeline import PipelineState


class TestRequirementsVerifierAgent:
    """测试需求验证官Agent"""

    def setup_method(self):
        """测试前置：创建mock LLM和Agent实例"""
        self.mock_llm = Mock(spec=ChatOpenAI)
        self.agent = RequirementsVerifierAgent(self.mock_llm)

    def test_init(self):
        """测试初始化"""
        assert self.agent.llm is self.mock_llm
        assert isinstance(self.agent, RequirementsVerifierAgent)
        assert self.agent.name() == "RequirementsVerifierAgent"

    def test_build_context_with_unanswered_questions(self):
        """测试构建上下文 - 包含未回答问题"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "是的"},
                {"question": "需要云同步吗？", "answer": None},
                {"question": "需要移动端吗？", "answer": None}
            ]
        )

        context = self.agent._build_context(state)

        assert "# 用户原始需求" in context
        assert "我需要一个待办事项APP" in context
        assert "# 完整问答历史" in context
        assert "# 当前待回答问题" in context
        assert "需要云同步吗？" in context
        assert "需要移动端吗？" in context
        assert "**状态**: 尚未回答" in context

    def test_build_context_all_answered(self):
        """测试构建上下文 - 所有问题已回答"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "是的"},
                {"question": "需要云同步吗？", "answer": "不需要"}
            ]
        )

        context = self.agent._build_context(state)

        assert "# 当前待回答问题" not in context
        assert "**用户回答**: 是的" in context
        assert "**用户回答**: 不需要" in context

    def test_parse_response_json_all_clear(self):
        """测试解析JSON响应 - 验证通过"""
        response_text = '''```json
{
    "all_clear": true,
    "additional_questions": []
}
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is True
        assert parsed["additional_questions"] == []

    def test_parse_response_json_with_additional_questions(self):
        """测试解析JSON响应 - 有额外问题需要追问"""
        response_text = '''```json
{
    "all_clear": false,
    "additional_questions": [
        "关于数据备份方案，您有什么要求？",
        "您期望的响应时间是多少？"
    ]
}
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["additional_questions"]) == 2

    def test_parse_response_text_all_clear(self):
        """测试解析文本响应 - 验证通过"""
        response_text = "所有关键问题都已经清晰，需求已经完整，可以进入下一阶段。ALL_CLEAR"
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is True
        assert len(parsed["additional_questions"]) == 0

    def test_parse_response_text_chinese_all_clear(self):
        """测试解析文本响应 - 中文表述验证通过"""
        response_text = "所有问题都已经澄清，需求已经清晰"
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is True

    def test_parse_response_text_with_additional_questions(self):
        """测试解析文本响应 - 列出额外问题"""
        response_text = '''
我发现还有以下问题需要澄清：
- 关于数据备份，您有什么要求？
- 系统需要支持多大并发？
'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["additional_questions"]) == 2

    def test_parse_response_numbered_questions(self):
        """测试解析文本响应 - 数字编号额外问题"""
        response_text = '''
还需要确认：
1. 您希望数据保留多长时间？
2. 是否需要审计日志功能？
'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["additional_questions"]) == 2

    def test_parse_response_with_code_block(self):
        """测试解析不带json标记的code块"""
        response_text = '''```
{
    "all_clear": false,
    "additional_questions": ["需要确认性能要求"]
}
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["additional_questions"]) == 1

    def test_run_verification_passed(self):
        """测试run方法 - 验证通过"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "需要多用户？", "answer": "不需要"},
                {"question": "需要移动端？", "answer": "需要"}
            ]
        )

        mock_response = MagicMock()
        mock_response.content = '''```json
{
    "all_clear": true,
    "additional_questions": []
}
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        assert result.requirements_verification_passed is True
        assert result.needs_more_questions is False
        # QA历史不变
        assert len(result.requirements_qa_history) == 2
        self.mock_llm.invoke.assert_called_once()

    def test_run_verification_failed_with_additional_questions(self):
        """测试run方法 - 验证不通过，添加额外问题"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "需要多用户？", "answer": "不需要"}
            ]
        )

        mock_response = MagicMock()
        mock_response.content = '''```json
{
    "all_clear": false,
    "additional_questions": [
        "您需要数据备份功能吗？",
        "是否需要分享功能？"
    ]
}
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        assert result.requirements_verification_passed is False
        assert result.needs_more_questions is True
        # 添加了两个新问题
        assert len(result.requirements_qa_history) == 3
        assert result.requirements_qa_history[1]["question"] == "您需要数据备份功能吗？"
        assert result.requirements_qa_history[1]["answer"] is None
        assert result.requirements_qa_history[2]["question"] == "是否需要分享功能？"
        self.mock_llm.invoke.assert_called_once()

    def test_run_updates_timestamp(self):
        """测试run方法更新时间戳"""
        import time
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )
        original_updated_at = state.updated_at

        # 确保至少过了一微秒
        time.sleep(0.0001)

        mock_response = MagicMock()
        mock_response.content = "ALL_CLEAR"
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        assert result.updated_at >= original_updated_at
