"""
Workflow Manager - 封装交互式流水线步进逻辑
复用所有现有的 Agent 和路由逻辑，给 Web 接口使用
"""
import os
from typing import Tuple, List, Dict
from langchain_openai import ChatOpenAI

from se_pipeline.types.pipeline import PipelineState
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.agents import (
    DocumentPreprocessorAgent,
    RequirementsAnalystAgent,
    RequirementsVerifierAgent,
    RequirementsFinalAgent,
)
from se_pipeline.quality_gate import AutoReviewer
from se_pipeline.graph.pipeline_graph import (
    analyst_node,
    verifier_node,
    final_node,
    after_analyst,
    after_verifier,
    after_quality_gate,
)


node_name_map = {
    "analyst": "需求分析师",
    "wait_user": "等待用户回答",
    "verifier": "需求验证官",
    "final": "需求生成",
    "quality_gate": "质量闸门",
    "__end__": "结束",
}


class WorkflowManager:
    """管理交互式工作流，复用所有现有逻辑"""

    def __init__(self, llm: ChatOpenAI, vision_llm: ChatOpenAI = None):
        self.llm = llm
        self.vision_llm = vision_llm or llm
        self.project_store = ProjectStore()

        # 一次性初始化所有 Agents，复用
        self.document_preprocessor = DocumentPreprocessorAgent(llm, vision_llm=vision_llm)
        self.analyst = RequirementsAnalystAgent(llm)
        self.verifier = RequirementsVerifierAgent(llm)
        self.finalizer = RequirementsFinalAgent(llm)
        self.reviewer = AutoReviewer(llm)

    def load_state(self, project_id: str) -> PipelineState:
        """加载项目状态"""
        return self.project_store.load_state(project_id)

    def save_state(self, project_id: str, state: PipelineState) -> None:
        """保存项目状态"""
        self.project_store.save_state(project_id, state)

    def get_unanswered_questions(self, state: PipelineState) -> List[Dict[str, str]]:
        """获取当前未回答的问题"""
        unanswered = []
        for item in state.requirements_qa_history:
            if item["answer"] is None:
                unanswered.append(item)
        return unanswered

    def run_step(self, state: PipelineState, current_node: str) -> Tuple[PipelineState, str]:
        """运行一个节点，返回(更新后的状态, 下一个节点)"""

        if current_node == "analyst":
            state = analyst_node(state, self.analyst)
            next_node = after_analyst(state)
        elif current_node == "verifier":
            state = verifier_node(state, self.verifier)
            next_node = after_verifier(state)
        elif current_node == "final":
            state = final_node(state, self.finalizer)
            next_node = "quality_gate"
        elif current_node == "quality_gate":
            if state.requirements_spec is not None:
                result = self.reviewer.review_requirements(state.requirements_spec)
                if not result.passed:
                    # 回流，更新状态，回到分析师
                    state = state.model_copy(update={
                        "requirements_verification_passed": False,
                        "needs_more_questions": True,
                        "backflow_feedback": result.feedback
                    })
            next_node = after_quality_gate(state)
        else:
            # unknown node, stay
            next_node = current_node

        # 保存状态
        self.save_state(state.project_id, state)
        return state, next_node

    def get_node_name(self, node: str) -> str:
        """获取节点中文名称"""
        return node_name_map.get(node, node)

    def process_documents(self, state: PipelineState) -> PipelineState:
        """文档预处理"""
        if not state.documents_processed and state.source_documents_dir:
            state = self.document_preprocessor.run(state)
            self.save_state(state.project_id, state)
        return state
