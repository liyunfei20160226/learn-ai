"""
集成测试: 最终需求生成Agent - 使用真实LLM
从项目根目录 .env 文件加载 OPENAI_API_KEY
"""
import os
import pytest
from dotenv import load_dotenv
from datetime import datetime
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_final import RequirementsFinalAgent
from se_pipeline.types.pipeline import PipelineState

# 加载 .env 文件
load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY 环境变量")
class TestRequirementsFinalAgentLLM:
    """使用真实LLM测试最终需求生成Agent"""

    @pytest.fixture(scope="class")
    def agent(self):
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        return RequirementsFinalAgent(llm)

    def test_generate_requirements_spec_from_qa(self, agent):
        """测试：从完整问答历史生成标准化需求规格"""
        state = PipelineState(
            project_id="integration-f-001",
            project_name="命令行待办APP",
            current_stage="requirements",
            original_user_requirement="我需要一个简单的命令行待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "不需要，只有我自己用"},
                {"question": "需要运行在什么平台？", "answer": "Linux 命令行环境"},
                {"question": "需要数据持久化吗？", "answer": "需要，退出后保存到本地文件"},
                {"question": "具体需要哪些核心功能？", "answer": "四个功能：新增待办、删除待办、列出所有待办、标记待办为完成"},
                {"question": "数据保存格式是什么？", "answer": "JSON文件存在当前目录"},
                {"question": "需要交互界面吗？", "answer": "简单的命令行交互即可"},
            ],
            requirements_verification_passed=True
        )

        result = agent.run(state)

        # 应该生成需求规格
        assert result.requirements_spec is not None
        spec = result.requirements_spec

        # 验证基本结构
        assert spec.project_id == "integration-f-001"
        assert spec.stage_id == "requirements"
        assert spec.verification_passed is True
        assert isinstance(spec.timestamp, datetime)

        # 验证数据字段
        data = spec.data
        assert len(data.title) > 0
        assert len(data.description) > 0
        assert len(data.functional_requirements) > 0

        # 验证问答历史
        qa = spec.qa_history
        assert len(qa.items) == 6
        assert qa.all_questions_answered is True

        print(f"\n[生成结果]:")
        print(f"  标题: {data.title}")
        print(f"  描述: {data.description[:100]}...")
        print(f"  功能需求数: {len(data.functional_requirements)}")
        print(f"  角色数: {len(data.user_roles)}")
        print(f"  不做范围: {data.out_of_scope}")

        # 打印功能需求
        print("\n  功能列表:")
        for fr in data.functional_requirements:
            priority = fr.get("priority", "unknown")
            print(f"    [{priority}] {fr.get('title', 'no title')}: {fr.get('description', '')[:50]}...")

    def test_generate_handles_incomplete_qa_still_works(self, agent):
        """测试：即使有未回答问题，仍然能生成当前状态的规格"""
        state = PipelineState(
            project_id="integration-f-002",
            project_name="待办APP半成品",
            current_stage="requirements",
            original_user_requirement="我需要一个待办APP",
            requirements_qa_history=[
                {"question": "需要多用户吗？", "answer": "不需要"},
                {"question": "需要移动端吗", "answer": None},
            ],
            requirements_verification_passed=False
        )

        result = agent.run(state)

        # 即使验证不通过，仍然应该生成制品
        assert result.requirements_spec is not None
        # 问答历史应该标记出未回答
        qa = result.requirements_spec.qa_history
        assert qa.all_questions_answered is False
        assert len(qa.remaining_questions) == 1
        print(f"\n[未完成问答生成]: remaining={qa.remaining_questions}")
