"""
集成测试: 完整需求分析流水线端到端测试 - 使用真实LLM

测试流程：手动步进，从 analyst → ... → end，每一步都显式处理，保证不会死循环
最多 8 步，肯定能走完
"""
import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.agents import (
    RequirementsAnalystAgent,
    RequirementsVerifierAgent,
    RequirementsFinalAgent,
)
from se_pipeline.quality_gate import AutoReviewer
from se_pipeline.graph.pipeline_graph import (
    analyst_node,
    verifier_node,
    final_node,
    quality_gate_node,
    after_analyst,
    after_verifier,
    after_quality_gate,
    wait_user_node,
)

load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要 OPENAI_API_KEY 环境变量")
class TestPipelineGraphEndToEnd:
    """完整需求分析流水线端到端集成测试"""

    def _auto_answer(self, state: PipelineState, max_total: int, answered_so_far: int) -> int:
        """自动回答所有未回答问题，返回新增回答数量"""
        added = 0
        for item in state.requirements_qa_history:
            if item["answer"] is None:
                q = item["question"].lower()
                if any(k in q for k in ["多用户", "账号", "登录", "注册"]):
                    item["answer"] = "是的，需要支持多用户账号登录"
                elif any(k in q for k in ["云同步", "同步", "跨设备"]):
                    item["answer"] = "需要云同步功能，支持跨设备访问"
                elif any(k in q for k in ["移动端", "手机", "app"]):
                    item["answer"] = "需要移动端App，同时支持网页版"
                elif any(k in q for k in ["分享", "协作"]):
                    item["answer"] = "需要基础的分享协作功能"
                elif "分类" in q or "标签" in q or "提醒" in q:
                    item["answer"] = "需要分类标签和到期提醒功能"
                else:
                    item["answer"] = "是的，需要这个功能"
                added += 1
        state.update_timestamp()
        return answered_so_far + added

    def test_full_graph_flow_simple_todo(self):
        """测试完整graph流程：简单待办事项APP，最多3个问题"""
        print("\n" + "="*60)
        print("[测试开始] 完整graph流程 - 简单待办事项APP")
        print("="*60)

        # 初始化
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        analyst = RequirementsAnalystAgent(llm)
        verifier = RequirementsVerifierAgent(llm)
        finalizer = RequirementsFinalAgent(llm)
        reviewer = AutoReviewer(llm)

        state = PipelineState(
            project_id="e2e-graph-test-001",
            project_name="个人待办APP",
            current_stage="requirements",
            original_user_requirement="我需要一个个人待办事项管理APP"
        )

        max_questions = 3
        answered = 0
        node = "analyst"
        steps = 0

        # 最多8步，绝对不会循环
        for _ in range(8):
            if node == "__end__":
                break
            steps += 1
            print(f"\n> 步骤 {steps}, 当前节点: {node}")

            if node == "analyst":
                state = analyst_node(state, analyst)
                node = after_analyst(state)
                continue

            if node == "wait_user":
                # 回答未回答问题
                unanswered = sum(1 for i in state.requirements_qa_history if i["answer"] is None)
                if unanswered > 0:
                    print(f"  LLM生成 {unanswered} 个问题:")
                    for i in state.requirements_qa_history:
                        if i["answer"] is None:
                            print(f"    - {i['question']}")
                    answered = self._auto_answer(state, max_questions, answered)
                    print(f"  自动回答完成，累计: {answered}/{max_questions}")

                # 如果超过限制，强制通过验证
                if answered >= max_questions:
                    print(f"  已达到问题限制 {max_questions}，强制设置验证通过")
                    state.requirements_verification_passed = True
                    state.needs_more_questions = False
                    state.update_timestamp()

                state = wait_user_node(state)
                node = "verifier"
                continue

            if node == "verifier":
                state = verifier_node(state, verifier)
                node = after_verifier(state)
                print(f"  验证完成，下一步: {node}")
                # 如果已经达到问答限制，强制进入final生成最终结果
                if answered >= max_questions and node == "analyst":
                    node = "final"
                    print(f"  [限制] 已达到问题限制 {max_questions}，强制进入final生成")
                continue

            if node == "final":
                print("  生成最终需求规格...")
                state = final_node(state, finalizer)
                node = "quality_gate"
                continue

            if node == "quality_gate":
                state = quality_gate_node(state, reviewer)
                node = after_quality_gate(state)
                print(f"  质量评审完成，下一步: {node}")
                continue

        # 循环结束后，如果验证已通过但还没到终点，继续推进
        if node != "__end__" and state.requirements_verification_passed:
            print("\n> 继续推进到终点（循环结束但验证已通过）")
            while node != "__end__" and steps < 12:
                steps += 1
                print(f"\n> 步骤 {steps}, 当前节点: {node}")
                if node == "final":
                    print("  生成最终需求规格...")
                    state = final_node(state, finalizer)
                    node = "quality_gate"
                elif node == "quality_gate":
                    state = quality_gate_node(state, reviewer)
                    node = after_quality_gate(state)
                    print(f"  质量评审完成，下一步: {node}")
                else:
                    break

        print("\n" + "="*60)
        print(f"[测试完成] 总步数: {steps}, 已回答问题: {answered}")
        print("="*60)

        # 验证
        assert state.requirements_spec is not None, "应该生成需求规格"
        assert state.requirements_spec.data.title is not None
        assert len(state.requirements_spec.data.title) > 0

        print("\n✓ 验证通过")
        print(f"  标题: {state.requirements_spec.data.title}")
        print(f"  功能需求: {len(state.requirements_spec.data.functional_requirements)} 项")
        print("  graph流程验证成功")

    def test_full_graph_flow_simple_calculator(self):
        """测试完整graph流程：非常简单清晰的需求"""
        print("\n" + "="*60)
        print("[测试开始] 完整graph流程 - 命令行计算器")
        print("="*60)

        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        analyst = RequirementsAnalystAgent(llm)
        verifier = RequirementsVerifierAgent(llm)
        finalizer = RequirementsFinalAgent(llm)
        reviewer = AutoReviewer(llm)

        state = PipelineState(
            project_id="e2e-graph-test-002",
            project_name="命令行计算器",
            current_stage="requirements",
            original_user_requirement="我需要一个命令行计算器，支持加减乘除四则运算，单用户本地使用，不需要网络。",
        )

        max_questions = 2
        answered = 0
        node = "analyst"
        steps = 0

        # 最多6步
        for _ in range(6):
            if node == "__end__":
                break
            print(f"\n> 步骤 {_+1}, 当前节点: {node}")

            if node == "analyst":
                state = analyst_node(state, analyst)
                node = after_analyst(state)
                continue

            if node == "wait_user":
                unanswered = sum(1 for i in state.requirements_qa_history if i["answer"] is None)
                if unanswered > 0:
                    print(f"  {unanswered} 个问题:")
                    for i in state.requirements_qa_history:
                        if i["answer"] is None:
                            print(f"    - {i['question']}")
                    answered = self._auto_answer(state, max_questions, answered)
                state = wait_user_node(state)
                node = "verifier"
                continue

            if node == "verifier":
                state = verifier_node(state, verifier)
                node = after_verifier(state)
                print(f"  验证完成，下一步: {node}")
                # 如果已经达到问答限制，强制进入final生成最终结果
                if answered >= max_questions and node == "analyst":
                    node = "final"
                    print(f"  [限制] 已达到问题限制 {max_questions}，强制进入final生成")
                continue

            if node == "final":
                print("  生成最终需求规格...")
                state = final_node(state, finalizer)
                node = "quality_gate"
                continue

            if node == "quality_gate":
                state = quality_gate_node(state, reviewer)
                node = after_quality_gate(state)
                print(f"  质量评审完成，下一步: {node}")
                break

            if node == "__end__":
                break

        # 循环结束后，如果验证已通过但还没到终点，继续推进
        if node != "__end__" and state.requirements_verification_passed:
            print("\n> 继续推进到终点")
            while node != "__end__" and steps < 10:
                steps += 1
                print(f"\n> 步骤 {steps}, 当前节点: {node}")
                if node == "final":
                    print("  生成最终需求规格...")
                    state = final_node(state, finalizer)
                    node = "quality_gate"
                elif node == "quality_gate":
                    state = quality_gate_node(state, reviewer)
                    node = after_quality_gate(state)
                    print(f"  质量评审完成，下一步: {node}")
                else:
                    break

        print("\n" + "="*60)
        print("[测试完成]")
        print("="*60)

        assert state.requirements_spec is not None
        assert state.requirements_spec.data.title is not None
        assert "计算器" in state.requirements_spec.data.title
        print("\n✓ 验证通过")
        print(f"  标题: {state.requirements_spec.data.title}")
