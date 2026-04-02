"""
最小化集成测试：只测试graph能走完一轮
"""
import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.agents import RequirementsAnalystAgent
from se_pipeline.graph.pipeline_graph import (
    analyst_node,
    after_analyst,
)

load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY 环境变量")
def test_graph_first_step():
    """测试graph第一步能正常执行"""
    print("\n=== 测试：graph第一步 ===\n")

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    analyst = RequirementsAnalystAgent(llm)

    state = PipelineState(
        project_id="minimal-test-001",
        project_name="测试",
        current_stage="requirements",
        original_user_requirement="我需要一个待办APP"
    )

    print("调用 analyst_node...")
    state = analyst_node(state, analyst)
    print(f"完成，问题数量: {len([i for i in state.requirements_qa_history if i['answer'] is None])}")
    print(f"needs_more_questions: {state.needs_more_questions}")

    next_node = after_analyst(state)
    print(f"after_analyst 返回: {next_node}")

    assert next_node == "wait_user"
    assert len(state.requirements_qa_history) > 0
    print("\n✓ 第一步测试通过")
