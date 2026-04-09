"""
流水线状态类型定义 - LangGraph 状态
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime

from .artifacts import RequirementsSpec


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
