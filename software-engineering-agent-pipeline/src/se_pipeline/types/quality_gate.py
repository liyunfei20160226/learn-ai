"""
质量闸门类型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CheckItem(BaseModel):
    """质量检查项"""
    id: str = Field(description="检查项ID")
    question: str = Field(description="检查问题")
    severity: Severity = Field(description="严重性级别")


class CheckResult(BaseModel):
    """单个检查项结果"""
    item: CheckItem = Field(description="检查项")
    passed: bool = Field(description="是否通过")
    feedback: str = Field(default="", description="反馈意见")


class QualityGateResult(BaseModel):
    """质量闸门检查结果"""
    stage_id: str = Field(description="检查的阶段")
    passed: bool = Field(description="整体是否通过")
    check_results: List[CheckResult] = Field(default_factory=list, description="所有检查结果")
    errors: List[CheckResult] = Field(default_factory=list, description="失败的error级检查项")
    warnings: List[CheckResult] = Field(default_factory=list, description="warning级检查项")
    feedback: str = Field(default="", description="整体反馈总结")
    target_stage_for_backflow: Optional[str] = Field(default=None, description="需要回流的目标阶段")
