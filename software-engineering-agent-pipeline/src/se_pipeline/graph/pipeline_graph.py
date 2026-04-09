"""
LangGraph流水线定义 - 完整软件工程流水线图
"""
from typing import Literal
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

from ..types.pipeline import PipelineState
from ..agents import (
    RequirementsAnalystAgent,
    RequirementsVerifierAgent,
    RequirementsFinalAgent,
)
from ..quality_gate import AutoReviewer


def analyst_node(state: PipelineState, analyst: RequirementsAnalystAgent) -> PipelineState:
    # 分析师总是基于完整问答历史重新分析，判断是否还需要提问
    # 这符合设计：分析师自己判断直到没有问题，才交给验证官
    return analyst.run(state)


def verifier_node(state: PipelineState, verifier: RequirementsVerifierAgent) -> PipelineState:
    # 标记已经进入验证阶段
    if not state.entered_verification:
        state = state.model_copy(update={"entered_verification": True})
    return verifier.run(state)


def final_node(state: PipelineState, finalizer: RequirementsFinalAgent) -> PipelineState:
    return finalizer.run(state)


def quality_gate_node(state: PipelineState, reviewer: AutoReviewer) -> PipelineState:
    """质量闸门自动评审"""
    if state.requirements_spec is not None:
        result = reviewer.review_requirements(state.requirements_spec)
        # 保存结果到state
        if not result.passed:
            # 质量不通过，需要回流
            state = state.model_copy(update={
                "requirements_verification_passed": False,
                "needs_more_questions": True
            })
    return state


def after_analyst(state: PipelineState) -> Literal["wait_user", "verifier"]:
    """分析师提问后，如果有未回答问题，等待用户回答
    如果分析师已经没有问题要问，所有问题都回答了，进入验证

    符合设计：分析师自己循环提问，直到觉得所有问题澄清，才交给验证官
    """
    has_unanswered = any(
        item["answer"] is None for item in state.requirements_qa_history
    )
    if has_unanswered:
        return "wait_user"  # 有新问题需要用户回答 → 等待用户输入
    else:
        if state.needs_more_questions:
            # 所有问题都回答了，但分析师说还需要继续提问 → 回到分析师自己
            # 分析师会基于新的问答历史，继续生成下一批问题
            return "analyst"
        else:
            # 分析师真的没问题了 → 交给验证官
            return "verifier"


def after_verifier(state: PipelineState) -> Literal["analyst", "wait_user", "final"]:
    """验证后：
    流程分为两个独立循环：
    1. 分析师循环：分析师提问→用户回答→分析师判断→循环直到分析师满意
    2. 验证官循环：验证官验证→发现遗漏追加问题→用户回答→验证官判断→循环直到验证官满意

    验证官开始后不再回分析师，独立完成验证循环。
    """
    has_unanswered = any(
        item["answer"] is None for item in state.requirements_qa_history
    )
    if has_unanswered:
        # 有未回答问题（刚添加的验证官追问）→ 去等待用户回答
        # 用户回答完自动回到 verifier，验证官再次验证
        return "wait_user"
    elif state.needs_more_questions:
        # 所有问题都回答了，但验证官判断还需要更多澄清 → 继续留在验证循环
        # 回到 verifier 让验证官再次检查并添加新问题
        return "verifier"
    else:
        # 验证官也满意了 → 进入最终生成
        return "final"


def wait_user_node(state: PipelineState) -> PipelineState:
    """等待用户回答节点 - 占位节点，不修改状态，用于外部暂停获取用户输入"""
    return state


def after_quality_gate(state: PipelineState) -> Literal["__end__", "analyst"]:
    """质量检查后，如果通过就结束，不通过回流到分析师"""
    if (state.requirements_spec is not None and
        state.requirements_verification_passed and
        not state.needs_more_questions):
        return "__end__"
    else:
        return "analyst"


def build_requirements_internal_graph(
    llm: ChatOpenAI
) -> StateGraph:
    """构建需求分析阶段内部的子图

    内部流程：双Agent交互式澄清循环

    Node:
    1. analyst - 需求分析师提问
    2. wait_user - 暂停等待用户回答（这里需要外部交互）→ 这是一个停止点，给用户输入机会
    3. verifier - 需求验证官验证
    4. final - 生成最终需求规格
    5. quality_gate - 自动质量评审
    """
    graph = StateGraph(PipelineState)

    # 初始化Agent
    analyst = RequirementsAnalystAgent(llm)
    verifier = RequirementsVerifierAgent(llm)
    finalizer = RequirementsFinalAgent(llm)
    reviewer = AutoReviewer(llm)

    # 定义节点 - 使用闭包绑定agent实例
    def analyst_node_bound(state: PipelineState) -> PipelineState:
        return analyst_node(state, analyst)

    def verifier_node_bound(state: PipelineState) -> PipelineState:
        return verifier_node(state, verifier)

    def final_node_bound(state: PipelineState) -> PipelineState:
        return final_node(state, finalizer)

    def quality_gate_node_bound(state: PipelineState) -> PipelineState:
        return quality_gate_node(state, reviewer)

    graph.add_node("analyst", analyst_node_bound)
    graph.add_node("wait_user", wait_user_node)  # 占位节点，表示需要外部等待用户输入
    graph.add_node("verifier", verifier_node_bound)
    graph.add_node("final", final_node_bound)
    graph.add_node("quality_gate", quality_gate_node_bound)

    # 定义边 - 从分析师开始
    graph.set_entry_point("analyst")

    # 添加条件边
    graph.add_conditional_edges("analyst", after_analyst)

    # wait_user 完成后 -> verifier，在外部调用中，每次invoke到这里就结束了
    # wait_user 可以被invoke，所以不设置finish，让外部控制每次运行到这里就停止
    graph.add_edge("wait_user", "verifier")

    # 验证后判断
    graph.add_conditional_edges("verifier", after_verifier)

    graph.add_edge("final", "quality_gate")

    # 添加条件边
    graph.add_conditional_edges("quality_gate", after_quality_gate)

    # 两个终点：__end__ 表示完成，wait_user 表示需要用户输入
    graph.set_finish_point("quality_gate")
    graph.set_finish_point("wait_user")

    return graph


def create_requirements_internal_app(llm: ChatOpenAI):
    """创建需求分析阶段内部子图应用"""
    graph = build_requirements_internal_graph(llm)
    return graph.compile()
