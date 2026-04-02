"""
制品类型定义 - 每个阶段输出的标准化制品
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class BaseArtifact(BaseModel):
    """所有制品的基类"""
    version: str = Field(default="1.0", description="制品格式版本")
    stage_id: str = Field(description="阶段ID")
    project_id: str = Field(description="项目ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="生成时间戳")
    data: Dict[str, Any] = Field(default_factory=dict, description="额外数据")


class QaHistoryItem(BaseModel):
    """问答历史条目 - 需求分析阶段的提问回答记录"""
    question_id: str = Field(description="问题ID")
    question: str = Field(description="问题内容")
    answer: Optional[str] = Field(default=None, description="用户回答，None表示还没回答")
    created_at: datetime = Field(default_factory=datetime.now, description="问题创建时间")
    answered_at: Optional[datetime] = Field(default=None, description="回答时间")


class RequirementsQaHistory(BaseModel):
    """需求分析问答历史"""
    items: List[QaHistoryItem] = Field(default_factory=list, description="问答列表")
    all_questions_answered: bool = Field(default=False, description="是否所有问题都已回答")
    remaining_questions: List[str] = Field(default_factory=list, description="待回答问题ID列表")


class RequirementsSpec(BaseArtifact):
    """需求规格制品"""
    class RequirementsData(BaseModel):
        title: str = Field(description="项目标题")
        description: str = Field(description="项目概述")
        requirements: List[Dict[str, str]] = Field(
            default_factory=list,
            description="需求列表，每项包含 id, title, description, priority"
        )
        functional_requirements: List[Dict[str, str]] = Field(default_factory=list)
        non_functional_requirements: List[Dict[str, str]] = Field(default_factory=list)
        user_roles: List[Dict[str, str]] = Field(default_factory=list)
        out_of_scope: List[str] = Field(default_factory=list, description="明确不做的范围")

    data: RequirementsData = Field(description="需求规格数据")
    qa_history: RequirementsQaHistory = Field(default_factory=RequirementsQaHistory, description="问答历史")
    verification_passed: bool = Field(default=False, description="需求验证官是否验证通过")
