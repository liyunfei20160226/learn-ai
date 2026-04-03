"""
单元测试: 自动评审器 AutoReviewer
"""
from unittest.mock import Mock, MagicMock
from langchain_openai import ChatOpenAI
from se_pipeline.quality_gate.auto_reviewer import AutoReviewer
from se_pipeline.types.quality_gate import QualityGateResult, Severity
from se_pipeline.types.artifacts import RequirementsSpec


class TestAutoReviewer:
    """测试自动评审器 AutoReviewer"""

    def setup_method(self):
        """测试前置：创建mock LLM和AutoReviewer实例"""
        self.mock_llm = Mock(spec=ChatOpenAI)
        self.reviewer = AutoReviewer(self.mock_llm)

    def test_init(self):
        """测试初始化"""
        assert self.reviewer.llm is self.mock_llm
        assert isinstance(self.reviewer, AutoReviewer)

    def test_build_review_prompt(self):
        """测试构建评审prompt"""
        # 创建测试需求规格
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="Test Todo Project",
                description="This is a test project",
                functional_requirements=[{"id": "1", "title": "Create todo"}],
                user_roles=[{"id": "1", "name": "Regular User"}]
            )
        )

        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        prompt = self.reviewer._build_review_prompt("Requirements Review", spec, checklist)

        # 验证prompt包含关键信息
        assert "# Requirements Review阶段质量评审" in prompt
        assert "项目标题: Test Todo Project" in prompt
        assert "项目描述: This is a test project" in prompt
        assert "功能需求数量: 1" in prompt
        assert "用户角色数量: 1" in prompt
        assert "检查清单" in prompt
        assert "输出JSON格式" in prompt

    def test_parse_result_json_with_code_block(self):
        """测试解析结果 - JSON在```json块中"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "All requirements are clear"
    },
    {
      "id": "complete",
      "passed": false,
      "feedback": "Missing some user requirements"
    }
  ]
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert isinstance(result, QualityGateResult)
        assert result.stage_id == "requirements"
        assert len(result.check_results) == 2
        assert result.passed is False  # 有一个ERROR级失败
        assert len(result.errors) == 1
        assert result.errors[0].item.id == "complete"

    def test_parse_result_json_with_plain_code_block(self):
        """测试解析结果 - JSON在不带json标记的```块中"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "All requirements are clear"
    }
  ]
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is True
        assert len(result.check_results) == 1
        assert len(result.errors) == 0

    def test_parse_result_plain_json_no_block(self):
        """测试解析结果 - 纯JSON没有代码块"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "OK"
    },
    {
      "id": "complete",
      "passed": true,
      "feedback": "OK"
    }
  ]
}
'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is True
        assert len(result.check_results) == 2
        assert len(result.errors) == 0
        assert result.feedback == "所有检查通过"

    def test_parse_result_with_only_warnings(self):
        """测试解析结果 - 只有警告，没有错误，应该通过"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        # 找到一个WARNING级别的检查项测试
        warning_item_id = None
        for item in checklist:
            if item.severity == Severity.WARNING:
                warning_item_id = item.id
                break

        if warning_item_id:
            response_text = f'''```json
{{
  "results": [
    {{
      "id": "{warning_item_id}",
      "passed": false,
      "feedback": "Can be improved"
    }}
  ]
}}
```'''

            result = self.reviewer._parse_result(response_text, checklist, "requirements")

            assert result.passed is True  # 只有警告仍然通过
            assert len(result.warnings) == 1
            assert len(result.errors) == 0
            assert "Can be improved" in result.feedback

    def test_parse_result_invalid_json(self):
        """测试解析结果 - JSON解析失败"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = "This is not valid JSON, just plain text"

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is True  # 解析失败默认通过
        assert "JSON解析失败" in result.feedback

    def test_parse_result_ignores_unknown_check_item(self):
        """测试解析结果 - 忽略未知的检查项ID"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "OK"
    },
    {
      "id": "non-existent-item",
      "passed": false,
      "feedback": "This should be ignored"
    }
  ]
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert len(result.check_results) == 1  # 只有已知项被包含
        assert result.passed is True

    def test_parse_result_empty_results(self):
        """测试解析结果 - 空结果数组"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```json
{
  "results": []
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is True
        assert len(result.check_results) == 0
        assert result.feedback == "所有检查通过"

    def test_parse_result_sets_target_stage_for_backflow_when_failed(self):
        """测试解析结果 - 失败时设置回流目标阶段"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": false,
      "feedback": "Some requirements are unclear"
    }
  ]
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is False
        assert result.target_stage_for_backflow == "requirements"

    def test_parse_result_no_backflow_when_passed(self):
        """测试解析结果 - 通过时不设置回流目标"""
        from se_pipeline.quality_gate.checklists import get_requirements_checklist
        checklist = get_requirements_checklist()

        response_text = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "OK"
    }
  ]
}
```'''

        result = self.reviewer._parse_result(response_text, checklist, "requirements")

        assert result.passed is True
        assert result.target_stage_for_backflow is None

    def test_review_requirements_success(self):
        """测试评审需求规格 - 成功路径"""
        # 创建测试需求规格
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="Test Project",
                description="This is a test description",
                functional_requirements=[],
                user_roles=[]
            )
        )

        # Mock LLM响应
        mock_response = MagicMock()
        mock_response.content = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": true,
      "feedback": "Requirements are clear"
    },
    {
      "id": "complete",
      "passed": true,
      "feedback": "All requirements are covered"
    }
  ]
}
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.reviewer.review_requirements(spec)

        assert isinstance(result, QualityGateResult)
        assert result.passed is True
        assert result.stage_id == "requirements"
        self.mock_llm.invoke.assert_called_once()
        # 验证prompt被正确传递
        called_prompt = self.mock_llm.invoke.call_args[0][0]
        assert "Test Project" in called_prompt
        assert "This is a test description" in called_prompt

    def test_review_requirements_failed(self):
        """测试评审需求规格 - 失败路径"""
        # 创建测试需求规格
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="",
                description="",
                functional_requirements=[],
                user_roles=[]
            )
        )

        # Mock LLM响应 - 多个检查项失败
        mock_response = MagicMock()
        mock_response.content = '''```json
{
  "results": [
    {
      "id": "clear",
      "passed": false,
      "feedback": "Some requirements are unclear"
    },
    {
      "id": "complete",
      "passed": false,
      "feedback": "Not all requirements are covered"
    }
  ]
}
```'''
        self.mock_llm.invoke.return_value = mock_response

        result = self.reviewer.review_requirements(spec)

        assert result.passed is False
        assert len(result.errors) > 0
        assert result.target_stage_for_backflow == "requirements"
        assert "发现" in result.feedback
        assert "Some requirements are unclear" in result.feedback
