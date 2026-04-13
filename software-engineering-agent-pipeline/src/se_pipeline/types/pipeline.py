"""
流水线状态类型定义 - LangGraph 状态
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime

from .artifacts import (
    RequirementsSpec,
    ArchitectureDesign,
    UIPrototype,
    DatabaseSchema,
    TaskBacklog,
    CodegenImplementation,
    CodeStructure,
    FrontendReviewResult,
    BackendReviewResult,
    DatabaseAnalysisResult,
    ConsistencyCheckResult,
    CodeReviewReport,
    TestReport,
    PreReleaseCheck,
    DeploymentConfig,
)


class AttachedDocument(BaseModel):
    """附加文档 - 用户导入的项目参考资料"""
    filename: str = Field(description="原始文件名")
    relative_path: str = Field(description="相对于资料根目录的路径")
    absolute_path: str = Field(description="原始绝对路径")
    original_ext: str = Field(description="原始文件扩展名")
    processed_pdf_path: Optional[str] = Field(default=None, description="转换后的PDF文件路径")
    page_image_paths: List[str] = Field(default_factory=list, description="PDF分页转换后的图片路径列表")
    file_size: int = Field(description="原始文件大小（字节）")
    summary_path: Optional[str] = Field(default=None, description="LLM总结后的summary.md文件相对路径（相对于项目processed_docs目录）")
    processed_at: datetime = Field(default_factory=datetime.now, description="处理完成时间")
    parse_success: bool = Field(default=False, description="是否解析成功")
    error_message: Optional[str] = Field(default=None, description="解析失败原因")


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

# 代码评审内部阶段（分步处理）
CodeReviewStageId = Literal[
    "code_structure",
    "frontend_review",
    "backend_review",
    "database_analyze",
    "consistency_check",
    "code_report",
]


class PipelineState(BaseModel):
    """流水线整体状态"""
    project_id: str = Field(description="项目ID")
    project_name: str = Field(description="项目名称")
    project_type: str = Field(default="full_development", description="项目类型: full_development (全新开发) / code_review (独立代码评审)")
    current_stage: StageId = Field(description="当前阶段")
    current_codereview_stage: Optional[CodeReviewStageId] = Field(default=None, description="代码评审当前内部阶段")
    original_user_requirement: str = Field(description="用户原始需求")

    # 各阶段制品
    requirements_spec: Optional[RequirementsSpec] = Field(default=None, description="需求规格制品")
    architecture_design: Optional[ArchitectureDesign] = Field(default=None, description="架构设计制品")
    ui_prototype: Optional[UIPrototype] = Field(default=None, description="UI原型制品")
    database_schema: Optional[DatabaseSchema] = Field(default=None, description="数据库设计制品")
    task_backlog: Optional[TaskBacklog] = Field(default=None, description="任务拆分制品")
    codegen_implementation: Optional[CodegenImplementation] = Field(default=None, description="代码生成制品")

    # 代码评审相关（独立代码评审模式或流水线阶段）
    target_code_dir: Optional[str] = Field(default=None, description="待评审的目标代码目录（绝对路径）")
    code_structure: Optional[CodeStructure] = Field(default=None, description="代码结构分析结果")
    frontend_review: Optional[FrontendReviewResult] = Field(default=None, description="前端评审结果")
    backend_review: Optional[BackendReviewResult] = Field(default=None, description="后端评审结果")
    database_analysis: Optional[DatabaseAnalysisResult] = Field(default=None, description="数据库分析结果")
    consistency_check: Optional[ConsistencyCheckResult] = Field(default=None, description="一致性检查结果")
    codereview_report: Optional[CodeReviewReport] = Field(default=None, description="最终代码评审报告")

    # 后续阶段制品
    test_report: Optional[TestReport] = Field(default=None, description="测试报告制品")
    pre_release_check: Optional[PreReleaseCheck] = Field(default=None, description="预发布检查制品")
    deployment_config: Optional[DeploymentConfig] = Field(default=None, description="部署配置制品")

    # 需求分析阶段内部状态（双Agent协作）
    requirements_qa_history: List[Dict[str, Optional[str]]] = Field(default_factory=list, description="问答历史")
    requirements_verification_passed: bool = Field(default=False, description="需求验证是否通过")
    needs_more_questions: bool = Field(default=False, description="是否需要继续提问（分析师或验证官需要继续）")
    entered_verification: bool = Field(default=False, description="是否已经进入验证阶段")

    # 回流相关
    backflow_target_stage: Optional[StageId] = Field(default=None, description="回流目标阶段")
    backflow_feedback: Optional[str] = Field(default=None, description="回流反馈意见")

    # 文档预处理
    project_background: str = Field(default="", description="预处理后的项目背景资料（所有文档总结拼接）")
    attached_documents: List[AttachedDocument] = Field(default_factory=list, description="导入的附加文档列表")
    documents_processed: bool = Field(default=False, description="是否已完成文档预处理")
    source_documents_dir: Optional[str] = Field(default=None, description="用户提供的原始资料目录路径")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    def update_timestamp(self) -> None:
        """更新时间戳"""
        self.updated_at = datetime.now()
