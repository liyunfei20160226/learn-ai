"""
单元测试: 最终需求生成Agent RequirementsFinalAgent
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_final import RequirementsFinalAgent
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.types.artifacts import RequirementsSpec, RequirementsQaHistory, QaHistoryItem


class TestRequirementsFinalAgent:
    """测试最终需求生成Agent"""

    def setup_method(self):
        """测试前置：创建mock LLM和Agent实例"""
        self.mock_llm = Mock(spec=ChatOpenAI)
        self.agent = RequirementsFinalAgent(self.mock_llm)

    def test_init(self):
        """测试初始化"""
        assert self.agent.llm is self.mock_llm
        assert isinstance(self.agent, RequirementsFinalAgent)

    def test_build_context(self):
        """测试构建上下文"""
        state = PipelineState(
            project_id="test-001",
            project_name="待办事项APP",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP来管理我的日常任务",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "是的，需要账号登录"},
                {"question": "需要云同步吗？", "answer": "是的，跨设备同步"},
            ]
        )

        context = self.agent._build_context(state)

        assert "# 项目信息" in context
        assert "项目名称: 待办事项APP" in context
        assert "用户原始需求: 我需要一个待办事项APP来管理我的日常任务" in context
        assert "# 完整问答澄清历史" in context
        assert "第1轮问答" in context
        assert "**问题**: 您需要支持多用户吗？" in context
        assert "**用户回答**: 是的，需要账号登录" in context
        assert "第2轮问答" in context
        assert "整理生成一份标准化的需求规格文档，输出YAML格式" in context

    def test_parse_response_yaml_from_code_block(self):
        """测试解析YAML响应 - 从代码块提取"""
        response_text = '''```yaml
title: 待办事项管理APP
description: 一个帮助用户管理日常任务的移动应用
requirements: []
functional_requirements:
  - id: FR001
    title: 用户注册登录
    description: 用户可以通过邮箱注册账号并登录
    priority: high
non_functional_requirements: []
user_roles:
  - name: 普通用户
    description: 使用待办管理功能
out_of_scope: []
```'''
        parsed = self.agent._parse_response(response_text)

        assert parsed["title"] == "待办事项管理APP"
        assert "移动应用" in parsed["description"]
        assert len(parsed["functional_requirements"]) == 1
        assert parsed["functional_requirements"][0]["id"] == "FR001"
        assert len(parsed["user_roles"]) == 1

    def test_parse_response_plain_yaml(self):
        """测试解析纯YAML响应 - 没有代码块"""
        response_text = '''
title: 测试项目
description: 测试描述
requirements: []
functional_requirements: []
non_functional_requirements: []
user_roles: []
out_of_scope:
  - 不做移动端
'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["title"] == "测试项目"
        assert "不做移动端" in parsed["out_of_scope"]

    def test_parse_response_with_generic_code_block(self):
        """测试解析不带yaml标记的代码块"""
        response_text = '''```
title: 测试项目
description: 测试描述
requirements: []
functional_requirements: []
non_functional_requirements: []
user_roles: []
out_of_scope: []
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["title"] == "测试项目"

    def test_parse_response_invalid_yaml_fallback(self):
        """测试解析无效YAML - 返回默认结构"""
        response_text = "这不是有效的YAML，格式错误了"
        parsed = self.agent._parse_response(response_text)

        # 应该返回默认空结构
        assert "title" in parsed
        assert "description" in parsed
        assert "requirements" in parsed
        assert "functional_requirements" in parsed
        assert "non_functional_requirements" in parsed
        assert "user_roles" in parsed
        assert "out_of_scope" in parsed

    def test_parse_response_clean_markdown(self):
        """测试解析YAML - 清理markdown标记后成功"""
        response_text = '''```yaml
title: Cleaned
description: Test
requirements: []
functional_requirements: []
non_functional_requirements: []
user_roles: []
out_of_scope: []
```'''
        parsed = self.agent._parse_response(response_text)
        assert parsed["title"] == "Cleaned"

    def test_build_qa_history_all_answered(self):
        """测试构建问答历史 - 所有问题已回答"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="测试需求",
            requirements_qa_history=[
                {"question": "问题1", "answer": "回答1"},
                {"question": "问题2", "answer": "回答2"},
            ]
        )

        qa_history = self.agent._build_qa_history(state)

        assert isinstance(qa_history, RequirementsQaHistory)
        assert len(qa_history.items) == 2
        assert qa_history.all_questions_answered is True
        assert len(qa_history.remaining_questions) == 0

        # 检查第一个item
        first_item = qa_history.items[0]
        assert isinstance(first_item, QaHistoryItem)
        assert first_item.question_id == "q1"
        assert first_item.question == "问题1"
        assert first_item.answer == "回答1"

    def test_build_qa_history_with_unanswered(self):
        """测试构建问答历史 - 有未回答问题"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="测试需求",
            requirements_qa_history=[
                {"question": "问题1", "answer": "回答1"},
                {"question": "问题2", "answer": None},
                {"question": "问题3", "answer": "回答3"},
            ]
        )

        qa_history = self.agent._build_qa_history(state)

        assert len(qa_history.items) == 3
        assert qa_history.all_questions_answered is False
        assert len(qa_history.remaining_questions) == 1
        assert "q2" in qa_history.remaining_questions

    def test_build_qa_history_empty(self):
        """测试构建问答历史 - 空历史"""
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="测试需求",
            requirements_qa_history=[]
        )

        qa_history = self.agent._build_qa_history(state)

        assert len(qa_history.items) == 0
        assert qa_history.all_questions_answered is True
        assert len(qa_history.remaining_questions) == 0

    def test_run_creates_requirements_spec(self):
        """测试run方法 - 成功生成需求规格制品"""
        state = PipelineState(
            project_id="test-001",
            project_name="待办事项APP",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "需要多用户？", "answer": "是的"},
                {"question": "需要云同步？", "answer": "是的"},
            ],
            requirements_verification_passed=True
        )

        # Mock LLM响应
        mock_response = MagicMock()
        mock_response.content = '''```yaml
title: 待办事项管理APP
description: 个人待办事项管理应用
requirements: []
functional_requirements:
  - id: FR001
    title: 用户登录
    description: 用户登录功能
    priority: high
non_functional_requirements: []
user_roles:
  - name: 普通用户
    description: 使用待办功能
out_of_scope:
  - 不做企业版
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.agent.run(state)

        # 验证生成了requirements_spec
        assert result.requirements_spec is not None
        assert isinstance(result.requirements_spec, RequirementsSpec)
        assert result.requirements_spec.stage_id == "requirements"
        assert result.requirements_spec.project_id == "test-001"
        assert result.requirements_spec.verification_passed is True
        assert isinstance(result.requirements_spec.timestamp, datetime)

        # 验证数据正确解析
        assert result.requirements_spec.data.title == "待办事项管理APP"
        assert len(result.requirements_spec.data.functional_requirements) == 1
        assert result.requirements_spec.data.out_of_scope == ["不做企业版"]

        # 验证问答历史
        assert isinstance(result.requirements_spec.qa_history, RequirementsQaHistory)
        assert len(result.requirements_spec.qa_history.items) == 2

        self.mock_llm.invoke.assert_called_once()
