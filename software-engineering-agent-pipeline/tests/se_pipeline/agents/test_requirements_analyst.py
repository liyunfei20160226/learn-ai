"""
单元测试: 需求分析师Agent RequirementsAnalystAgent
"""
from unittest.mock import Mock, MagicMock
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_analyst import RequirementsAnalystAgent
from se_pipeline.types.pipeline import PipelineState


class TestRequirementsAnalystAgent:
    """测试需求分析师Agent"""

    def setup_method(self):
        """测试前置：创建mock LLM和Agent实例"""
        self.mock_llm = Mock(spec=ChatOpenAI)
        self.agent = RequirementsAnalystAgent(self.mock_llm)

    def test_init(self):
        """测试初始化"""
        assert self.agent.llm is self.mock_llm
        assert isinstance(self.agent, RequirementsAnalystAgent)

    def test_build_context_with_empty_history(self):
        """测试构建上下文 - 空问答历史"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )

        context = self.agent._build_context(state)

        assert "# 用户原始需求" in context
        assert "我需要一个待办事项APP" in context
        assert "# 当前问答历史" in context

    def test_build_context_with_qa_history(self):
        """测试构建上下文 - 有问答历史"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "是的，需要账号登录"},
                {"question": "需要移动端支持吗？", "answer": None}
            ]
        )

        context = self.agent._build_context(state)

        assert "第1轮" in context
        assert "**问题**: 您需要支持多用户吗？" in context
        assert "**回答**: 是的，需要账号登录" in context
        assert "第2轮" in context
        assert "**问题**: 需要移动端支持吗？" in context

    def test_parse_response_yaml_all_clear(self):
        """测试解析YAML响应 - ALL_CLEAR"""
        response_text = '''```yaml
all_clear: true
questions: []
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is True
        assert parsed.get("questions", []) == []

    def test_parse_response_yaml_with_questions(self):
        """测试解析YAML响应 - 有问题列表"""
        response_text = '''```yaml
all_clear: false
questions:
  - 您需要支持多用户吗？
  - 需要移动端支持吗？
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 2
        assert "您需要支持多用户吗？" in parsed["questions"]

    def test_parse_response_plain_text_all_clear(self):
        """测试解析纯文本响应 - ALL_CLEAR"""
        response_text = "所有问题都已经澄清，ALL_CLEAR"
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is True

    def test_parse_response_plain_text_bullet_points(self):
        """测试解析纯文本响应 - 列表形式问题"""
        response_text = '''
我需要向您确认几个问题：
- 您需要支持多用户登录吗？
- 您希望有移动端版本吗？
- 需要数据云同步吗？
'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 3
        assert "您需要支持多用户登录吗？" in parsed["questions"]

    def test_parse_response_plain_text_numbered(self):
        """测试解析纯文本响应 - 数字编号问题"""
        response_text = '''
1. 您需要支持多用户登录吗？
2. 您希望有移动端版本吗？
'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 2

    def test_parse_response_single_question(self):
        """测试解析单问题响应 - 整段就是一个问题"""
        response_text = "请问您的应用需要支持多人协作编辑待办事项吗？"
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 1
        assert "需要支持多人协作编辑" in parsed["questions"][0]

    def test_parse_response_with_code_block(self):
        """测试解析不带yaml标记的code块"""
        response_text = '''```
{
  "all_clear": false,
  "questions": ["测试问题"]
}
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 1

    def test_parse_response_yaml_block(self):
        """测试解析yaml代码块"""
        response_text = '''```yaml
all_clear: false
questions:
  - 测试问题
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["all_clear"] is False
        assert len(parsed["questions"]) == 1
        assert "测试问题" in parsed["questions"]

    def test_run_with_needs_more_questions(self):
        """测试run方法 - 需要继续提问"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )

        # Mock LLM响应
        mock_response = MagicMock()
        mock_response.content = '''```yaml
all_clear: false
questions:
  - 您需要支持多用户吗？
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        assert result.needs_more_questions is True
        assert len(result.requirements_qa_history) == 1
        assert result.requirements_qa_history[0]["question"] == "您需要支持多用户吗？"
        assert result.requirements_qa_history[0]["answer"] is None
        self.mock_llm.invoke.assert_called_once()

    def test_run_with_all_clear(self):
        """测试run方法 - 所有问题澄清完成"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "需要多用户吗？", "answer": "不需要"}
            ]
        )

        mock_response = MagicMock()
        mock_response.content = "all_clear: true"
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        assert result.needs_more_questions is False
        # QA历史保持不变
        assert len(result.requirements_qa_history) == 1
        self.mock_llm.invoke.assert_called_once()
