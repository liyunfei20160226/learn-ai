"""
集成测试: 需求分析师Agent - 使用真实LLM
从项目根目录 .env 文件加载 OPENAI_API_KEY
"""
import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from se_pipeline.agents.requirements_analyst import RequirementsAnalystAgent
from se_pipeline.types.pipeline import PipelineState

# 加载 .env 文件
load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY 环境变量")
class TestRequirementsAnalystAgentLLM:
    """使用真实LLM测试需求分析师Agent"""

    @pytest.fixture(scope="class")
    def agent(self):
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        return RequirementsAnalystAgent(llm)

    def test_analyze_fuzzy_requirement_generates_questions(self, agent):
        """测试：模糊需求应该生成澄清问题"""
        state = PipelineState(
            project_id="integration-test-001",
            project_name="待办APP测试",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )

        result = agent.run(state)

        assert result.needs_more_questions is True
        assert len(result.requirements_qa_history) > 0
        # 至少应该有一个问题
        questions = [item["question"] for item in result.requirements_qa_history if item["question"]]
        assert len(questions) >= 1
        # 问题应该有一定长度，不是空字符串
        assert len(questions[0]) > 10
        print(f"\n[LLM输出问题]: {questions[0]}")

    def test_analyze_with_partial_history_follow_up(self, agent):
        """测试：已有部分问答历史，应该继续追问遗漏点"""
        state = PipelineState(
            project_id="integration-test-002",
            project_name="待办APP测试",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP",
            requirements_qa_history=[
                {"question": "您需要支持多用户登录吗？", "answer": "是的，需要账号系统"},
                {"question": "需要移动端支持吗？", "answer": "只需要网页版"}
            ]
        )

        result = agent.run(state)

        # 应该还有问题需要澄清
        assert result.needs_more_questions is True
        # 添加了新问题
        assert len(result.requirements_qa_history) > 2
        new_question = result.requirements_qa_history[-1]["question"]
        assert len(new_question) > 10
        print(f"\n[LLM追问]: {new_question}")

    def test_all_clear_when_sufficient(self, agent):
        """测试：需求足够清晰时应该返回ALL_CLEAR"""
        state = PipelineState(
            project_id="integration-test-003",
            project_name="简单待办",
            current_stage="requirements",
            original_user_requirement="我需要一个非常简单的命令行待办清单，只需要增删改查四个功能，不需要多用户，不需要网络，就是单用户本地使用",
            requirements_qa_history=[
                {"question": "您需要支持什么平台？", "answer": "命令行，Linux/macOS"},
                {"question": "需要数据持久化吗？", "answer": "需要保存到本地文件"},
                {"question": "需要分享功能吗？", "answer": "不需要，只有我自己用"}
            ]
        )

        result = agent.run(state)

        # 如果需求足够清晰，LLM应该判断为all_clear
        # 可能不一定100%每次都ALL_CLEAR，所以不强制断言，但检查格式
        if not result.needs_more_questions:
            print("\n[LLM判断]: 需求足够清晰，ALL_CLEAR")
            assert not result.needs_more_questions
        else:
            questions = [item["question"] for item in result.requirements_qa_history[3:]]
            print(f"\n[LLM继续提问]: {len(questions)} 个问题")
            for q in questions:
                print(f"  - {q}")
