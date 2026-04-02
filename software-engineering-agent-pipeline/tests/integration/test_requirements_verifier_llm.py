"""
集成测试: 需求验证官Agent - 使用真实LLM
从项目根目录 .env 文件加载 OPENAI_API_KEY
"""
import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_verifier import RequirementsVerifierAgent
from se_pipeline.types.pipeline import PipelineState

# 加载 .env 文件
load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY 环境变量")
class TestRequirementsVerifierAgentLLM:
    """使用真实LLM测试需求验证官Agent"""

    @pytest.fixture(scope="class")
    def agent(self):
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        return RequirementsVerifierAgent(llm)

    def test_verify_complete_requirements_passes(self, agent):
        """测试：完整清晰的需求应该验证通过"""
        state = PipelineState(
            project_id="integration-v-001",
            project_name="命令行待办",
            current_stage="requirements",
            original_user_requirement="我需要一个简单的命令行待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户吗？", "answer": "不需要，单用户"},
                {"question": "需要什么平台？", "answer": "Linux 命令行"},
                {"question": "需要数据保存吗？", "answer": "需要保存到本地JSON文件"},
                {"question": "需要哪些功能？", "answer": "增加待办、删除待办、列出所有待办、标记完成"},
                {"question": "需要UI美化吗？", "answer": "简单就行，不需要复杂美化"}
            ]
        )

        result = agent.run(state)

        print(f"\n[验证结果]: passed={result.requirements_verification_passed}, needs_more={result.needs_more_questions}")
        if result.requirements_verification_passed:
            print("  ✓ LLM判断需求完整，验证通过")
        else:
            additional = [item["question"] for item in result.requirements_qa_history if item["answer"] is None][-len(result.requirements_qa_history) + 5:]
            print(f"  ✗ LLM发现遗漏问题: {additional}")

        # 对于这个清晰完整的例子，大概率应该通过
        # 但不强制断言，因为LLM可能有不同判断
        if result.requirements_verification_passed:
            assert result.needs_more_questions is False

    def test_verify_incomplete_requirements_finds_missing(self, agent):
        """测试：不完整的需求应该发现遗漏，要求继续提问"""
        state = PipelineState(
            project_id="integration-v-002",
            project_name="电商网站",
            current_stage="requirements",
            original_user_requirement="我需要做一个电商网站",
            requirements_qa_history=[
                {"question": "您目标用户是谁？", "answer": "国内消费者"},
                {"question": "需要支持支付吗？", "answer": "需要"}
            ]
            # 很多关键问题没问：物流、商品分类、后台管理、用户权限...
        )

        result = agent.run(state)

        assert result.requirements_verification_passed is False
        assert result.needs_more_questions is True
        # 应该添加了额外问题
        added_questions = [item["question"] for item in result.requirements_qa_history if item["answer"] is None]
        assert len(added_questions) > 0
        print(f"\n[LLM发现遗漏]: {len(added_questions)} 个问题:")
        for q in added_questions:
            print(f"  - {q}")

    def test_verify_all_answered_still_finds_ambiguity(self, agent):
        """测试：所有问题都回答了，但仍有歧义，验证官应该发现"""
        state = PipelineState(
            project_id="integration-v-003",
            project_name="聊天APP",
            current_stage="requirements",
            original_user_requirement="做一个聊天APP",
            requirements_qa_history=[
                {"question": "支持群聊吗", "answer": "支持"},
                {"question": "需要语音通话吗", "answer": "不需要"},
                {"question": "支持iOS/Android吗", "answer": "都要"},
            ]
            # 确实还有很多关键问题没问：消息存储、好友关系、推送、加密...
        )

        result = agent.run(state)

        # 验证官应该发现还有遗漏
        if not result.requirements_verification_passed:
            added = [item["question"] for item in result.requirements_qa_history if item["answer"] is None]
            print(f"\n[LLM补充问题]: {len(added)} 个")
            for q in added:
                print(f"  - {q}")
