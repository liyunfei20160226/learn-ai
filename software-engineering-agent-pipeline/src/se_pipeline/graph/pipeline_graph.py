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
from ..quality_gate.checklists import get_codereview_checklist


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


def after_codereview_quality_gate(state: PipelineState) -> str:
    """代码评审质量闸门后，按固定顺序进入下一步"""
    if state.code_structure is None:
        # code_structure 还没做，下一步 code_structure
        return "code_structure"
    elif state.frontend_review is None:
        # code_structure 已完成，frontend_review 还没做 → 下一步 frontend_review
        return "frontend_review"
    elif state.backend_review is None:
        # frontend_review 已完成，backend_review 还没做 → 下一步 backend_review
        return "backend_review"
    elif state.database_analysis is None:
        # backend_review 已完成，database_analyze 还没做 → 下一步 database_analyze
        return "database_analyze"
    elif state.consistency_check is None:
        # database_analyze 已完成，consistency_check 还没做 → 下一步 consistency_check
        return "consistency_check"
    elif state.codereview_report is None:
        # consistency_check 已完成，code_report 还没做 → 下一步 code_report
        return "code_report"
    else:
        # 全部完成
        return "__end__"


def codereview_quality_gate_node(state: PipelineState, reviewer: AutoReviewer) -> PipelineState:
    """质量闸门 - 每个阶段完成后都检查质量

    刚完成的阶段 = 下一个要做的阶段 的前一个阶段
    因为 after_codereview_quality_gate 返回的就是下一个要做的阶段
    """
    # 固定顺序
    stage_order = [
        "code_structure",
        "frontend_review",
        "backend_review",
        "database_analyze",
        "consistency_check",
        "code_report",
        "codereview_report",
    ]

    # 找出下一个要做的阶段
    next_stage = after_codereview_quality_gate(state)

    if next_stage == "__end__":
        # 全部完成了，评审最终报告
        current_stage = "codereview_report"
    else:
        # 找到下一个阶段在列表中的索引，前一个就是刚完成的需要评审
        try:
            idx = stage_order.index(next_stage)
            if idx > 0:
                current_stage = stage_order[idx - 1]
            else:
                # 还没有任何阶段完成
                return state
        except ValueError:
            # 未知阶段，直接返回
            return state

    if current_stage is None:
        # 还没有任何阶段完成，直接通过
        return state

    # 特殊处理：一致性检查，如果用户没有上传设计文档（project_background 为空），直接通过
    # 因为本来就没有内容需要对比，一致性检查会跳过
    if current_stage == "consistency_check":
        has_design_doc = False
        if state.project_background and state.project_background.strip():
            has_design_doc = True
        if state.attached_documents and any(doc.parse_success for doc in state.attached_documents):
            has_design_doc = True
        if not has_design_doc:
            # 没有设计文档可供对比，直接通过质量闸门
            state = state.model_copy(update={
                "backflow_target_stage": None,
                "backflow_feedback": None,
            })
            return state

    # 获取对应检查清单
    checklist_stage_map = {
        "code_structure": "code-structure",
        "frontend_review": "frontend-review",
        "backend_review": "backend-review",
        "database_analyze": "database-analysis",
        "consistency_check": "consistency-check",
        "codereview_report": None,
    }
    checklist = get_codereview_checklist(checklist_stage_map[current_stage])

    # 获取当前artifact
    artifact_map = {
        "code_structure": state.code_structure,
        "frontend_review": state.frontend_review,
        "backend_review": state.backend_review,
        "database_analyze": state.database_analysis,
        "consistency_check": state.consistency_check,
        "codereview_report": state.codereview_report,
    }
    artifact = artifact_map[current_stage]

    # 评审
    if current_stage == "codereview_report":
        # 最终报告，使用专用方法
        result = reviewer.review_codereview(artifact)
    else:
        # 中间阶段，使用泛化方法
        result = reviewer.review_artifact(artifact, current_stage, checklist)

    # 保存质量闸门评审结果到markdown文档（不管是否通过，都保存供人工查看）
    from se_pipeline.storage.project_store import ProjectStore
    store = ProjectStore()
    project_dir = store.get_project_dir(state.project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    stage_display_name = {
        "code_structure": "代码结构分析",
        "frontend_review": "前端代码评审",
        "backend_review": "后端代码评审",
        "database_analyze": "数据库分析",
        "consistency_check": "一致性检查",
        "codereview_report": "最终代码评审报告",
    }.get(current_stage, current_stage)

    lines = []
    lines.append(f"# 质量闸门评审结果 - {stage_display_name}")
    lines.append("")
    lines.append(f"**项目ID**: {state.project_id}")
    lines.append(f"**阶段**: {current_stage}")
    lines.append(f"**评审时间**: {state.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"**评审结果**: {'✅ 通过' if result.passed else '❌ 不通过'}")
    lines.append("")
    if result.feedback:
        lines.append("## 评审反馈")
        lines.append("")
        lines.append(result.feedback)
        lines.append("")

    md_filename = f"quality-gate-{current_stage}.md"
    md_path = project_dir / md_filename
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    if not result.passed:
        # 质量不通过，将当前阶段artifact设为None，让它回流重做
        # after_codereview_quality_gate会检测到None，自动回到这个阶段
        update_kwargs = {
            current_stage: None,
            "backflow_target_stage": result.target_stage_for_backflow,
            "backflow_feedback": result.feedback,
        }
        state = state.model_copy(update=update_kwargs)
    else:
        # 质量通过，清空回流反馈，进入下一步
        update_kwargs = {
            "backflow_target_stage": None,
            "backflow_feedback": None,
        }
        state = state.model_copy(update=update_kwargs)

    return state


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


def build_codereview_subgraph(
    llm: ChatOpenAI
) -> StateGraph:
    """构建代码评审阶段内部子图
    分步流程：
    code_structure → quality_gate → frontend_review → quality_gate → backend_review → quality_gate → database_analyze → quality_gate → consistency_check → quality_gate → code_report → quality_gate → end
    """
    from ..agents import (
        CodeStructureAgent,
        FrontendReviewAgent,
        BackendReviewAgent,
        DatabaseAnalyzeAgent,
        ConsistencyCheckAgent,
        CodeReportAgent,
    )
    from ..quality_gate import AutoReviewer

    graph = StateGraph(PipelineState)

    # 初始化各个Agent
    code_structure_agent = CodeStructureAgent(llm)
    frontend_agent = FrontendReviewAgent(llm)
    backend_agent = BackendReviewAgent(llm)
    database_agent = DatabaseAnalyzeAgent(llm)
    consistency_agent = ConsistencyCheckAgent(llm)
    report_agent = CodeReportAgent(llm)
    reviewer = AutoReviewer(llm)

    # 定义节点包装
    async def code_structure_node(state: PipelineState) -> PipelineState:
        return await code_structure_agent.run(state)

    async def frontend_review_node(state: PipelineState) -> PipelineState:
        return await frontend_agent.run(state)

    async def backend_review_node(state: PipelineState) -> PipelineState:
        return await backend_agent.run(state)

    async def database_analyze_node(state: PipelineState) -> PipelineState:
        return await database_agent.run(state)

    async def consistency_check_node(state: PipelineState) -> PipelineState:
        return await consistency_agent.run(state)

    async def code_report_node(state: PipelineState) -> PipelineState:
        return await report_agent.run(state)

    def codereview_quality_gate_node_bound(state: PipelineState) -> PipelineState:
        return codereview_quality_gate_node(state, reviewer)

    # 添加节点
    graph.add_node("code_structure", code_structure_node)
    graph.add_node("frontend_review", frontend_review_node)
    graph.add_node("backend_review", backend_review_node)
    graph.add_node("database_analyze", database_analyze_node)
    graph.add_node("consistency_check", consistency_check_node)
    graph.add_node("code_report", code_report_node)
    graph.add_node("codereview_quality_gate", codereview_quality_gate_node_bound)

    # 连接流程 - 每个步骤后过质量闸门
    graph.set_entry_point("code_structure")
    graph.add_edge("code_structure", "codereview_quality_gate")
    graph.add_edge("codereview_quality_gate", "frontend_review")
    graph.add_edge("frontend_review", "codereview_quality_gate")
    graph.add_edge("codereview_quality_gate", "backend_review")
    graph.add_edge("backend_review", "codereview_quality_gate")
    graph.add_edge("codereview_quality_gate", "database_analyze")
    graph.add_edge("database_analyze", "codereview_quality_gate")
    graph.add_edge("codereview_quality_gate", "consistency_check")
    graph.add_edge("consistency_check", "codereview_quality_gate")
    graph.add_edge("codereview_quality_gate", "code_report")
    graph.add_edge("code_report", "codereview_quality_gate")

    # 完成后结束
    graph.set_finish_point("codereview_quality_gate")

    return graph


def create_codereview_subgraph_app(llm: ChatOpenAI):
    """创建代码评审子图应用"""
    graph = build_codereview_subgraph(llm)
    return graph.compile()
