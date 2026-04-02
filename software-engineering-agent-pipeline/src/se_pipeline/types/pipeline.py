"""
流水线状态类型定义 - LangGraph 状态
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime

from .artifacts import RequirementsSpec


StageId = Literal[
    "requirements",
    "architecture",
    "ui_prototype",
    "database",
    "task_breakdown",
    "codegen",
    "codereview",
    "testing",
    "pre_release",
    "deployment",
]


class PipelineState(BaseModel):
    """流水线整体状态"""
    project_id: str = Field(description="项目ID")
    project_name: str = Field(description="项目名称")
    current_stage: StageId = Field(description="当前阶段")
    original_user_requirement: str = Field(description="用户原始需求")

    # 各阶段制品
    requirements_spec: Optional[RequirementsSpec] = Field(default=None, description="需求规格制品")

    # 需求分析阶段内部状态（双Agent协作）
    requirements_qa_history: List[Dict[str, Optional[str]]] = Field(default_factory=list, description="问答历史")
    requirements_verification_passed: bool = Field(default=False, description="需求验证是否通过")
    needs_more_questions: bool = Field(default=False, description="是否需要继续提问")

    # 回流相关
    backflow_target_stage: Optional[StageId] = Field(default=None, description="回流目标阶段")
    backflow_feedback: Optional[str] = Field(default=None, description="回流反馈意见")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()
