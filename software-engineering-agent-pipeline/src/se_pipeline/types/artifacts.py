"""
制品类型定义 - 每个阶段输出的标准化制品
"""
from __future__ import annotations
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


class CodeStructure(BaseArtifact):
    """代码结构分析制品 - 目录扫描与技术栈识别"""
    class FileTypeCount(BaseModel):
        extension: str = Field(description="文件扩展名")
        count: int = Field(description="文件数量")
        total_lines: int = Field(description="总行数")

    class DetectedTech(BaseModel):
        category: str = Field(description="技术类别 (frontend/backend/database/tooling)")
        name: str = Field(description="技术名称")
        version: Optional[str] = Field(default=None, description="识别出的版本")
        detection_source: str = Field(description="从哪里识别出来的 (文件名/配置文件)")

    class CodeStructureData(BaseModel):
        root_directory: str = Field(description="扫描的根目录")
        directory_tree: str = Field(description="文本格式目录树")
        file_types: List["FileTypeCount"] = Field(default_factory=list, description="各类型文件统计")  # noqa: F821
        detected_tech: List["DetectedTech"] = Field(default_factory=list, description="识别出的技术栈")  # noqa: F821
        frontend_detected: bool = Field(default=False, description="是否检测到前端代码")
        backend_detected: bool = Field(default=False, description="是否检测到后端代码")
        database_detected: bool = Field(default=False, description="是否检测到数据库相关代码")
        summary: str = Field(description="整体架构摘要")

    data: CodeStructureData = Field(description="代码结构分析数据")


class FrontendReviewResult(BaseArtifact):
    """前端代码评审结果制品"""
    class Issue(BaseModel):
        issue_id: str = Field(description="问题ID")
        location: str = Field(description="问题位置 (文件路径)")
        issue_type: str = Field(description="问题类型 (architecture/naming/style/complexity/performance/security)")
        severity: str = Field(description="严重程度 (error/warning/info)")
        description: str = Field(description="问题描述和原因")

    class FrontendReviewData(BaseModel):
        frontend_type: Optional[str] = Field(default=None, description="前端技术类型 (React/Vue/Angular/Vanilla)")
        directory_structure_review: str = Field(description="目录结构合理性评审意见")
        issues: List["Issue"] = Field(default_factory=list, description="发现的问题列表")  # noqa: F821
        summary: str = Field(description="前端评审总结")

    data: FrontendReviewData = Field(description="前端评审结果数据")


class BackendReviewResult(BaseArtifact):
    """后端代码评审结果制品"""
    class Issue(BaseModel):
        issue_id: str = Field(description="问题ID")
        location: str = Field(description="问题位置 (文件路径/模块)")
        issue_type: str = Field(description="问题类型 (architecture/naming/style/complexity/performance/security/error-handling)")
        severity: str = Field(description="严重程度 (error/warning/info)")
        description: str = Field(description="问题描述和原因")

    class BackendReviewData(BaseModel):
        backend_type: Optional[str] = Field(default=None, description="后端技术类型 (Python/Node.js/Java/Go/etc)")
        backend_framework: Optional[str] = Field(default=None, description="后端框架")
        directory_structure_review: str = Field(description="目录结构/模块划分合理性评审意见")
        issues: List["Issue"] = Field(default_factory=list, description="发现的问题列表")  # noqa: F821
        summary: str = Field(description="后端评审总结")

    data: BackendReviewData = Field(description="后端评审结果数据")


class DatabaseAnalysisResult(BaseArtifact):
    """数据库结构分析结果制品"""
    class Table(BaseModel):
        table_name: str = Field(description="表名")
        detected_from: str = Field(description="从哪里检测出来的 (ORM model/SQL file/migration)")
        columns: List[Dict[str, str]] = Field(default_factory=list, description="列定义")

    class Issue(BaseModel):
        issue_id: str = Field(description="问题ID")
        location: str = Field(description="问题位置 (表名/文件)")
        issue_type: str = Field(description="问题类型 (design/normalization/indexes/constraints)")
        severity: str = Field(description="严重程度 (error/warning/info)")
        description: str = Field(description="问题描述和原因")

    class DatabaseAnalysisData(BaseModel):
        database_type: Optional[str] = Field(default=None, description="数据库类型 (MySQL/PostgreSQL/SQLite/MongoDB/etc)")
        derived_tables: List["Table"] = Field(default_factory=list, description="从代码推导出的表列表")  # noqa: F821
        issues: List["Issue"] = Field(default_factory=list, description="发现的设计问题列表")  # noqa: F821
        summary: str = Field(description="数据库设计分析总结")

    data: DatabaseAnalysisData = Field(description="数据库分析结果数据")


class ConsistencyCheckResult(BaseArtifact):
    """一致性检查结果制品 - 对比代码和设计文档"""
    class Inconsistency(BaseModel):
        check_id: str = Field(description="检查项ID")
        location: str = Field(description="不一致位置")
        description: str = Field(description="不一致描述")
        severity: str = Field(description="严重程度 (error/warning)")

    class ConsistencyCheckData(BaseModel):
        design_document_available: bool = Field(default=False, description="是否有设计文档")
        total_checks: int = Field(default=0, description="总共检查项数")
        inconsistencies: List["Inconsistency"] = Field(default_factory=list, description="发现的不一致列表")  # noqa: F821
        summary: str = Field(description="一致性检查总结")
        overall_consistent: bool = Field(default=True, description="整体是否一致")

    data: ConsistencyCheckData = Field(description="一致性检查结果数据")


class CodeReviewIssue(BaseModel):
    """代码评审问题 - 最终汇总"""
    issue_id: str = Field(description="问题ID")
    category: str = Field(description="分类 (structure/frontend/backend/database/consistency)")
    location: str = Field(description="问题位置")
    issue_type: str = Field(description="问题类型")
    severity: str = Field(description="严重程度 (error/warning/info)")
    description: str = Field(description="问题描述和原因")


class CodeReviewReport(BaseArtifact):
    """最终代码评审报告制品"""
    class CodeReviewData(BaseModel):
        target_directory: str = Field(description="评审的目标目录")
        detected_tech_summary: str = Field(description="识别出的技术栈摘要")
        issues: List[CodeReviewIssue] = Field(default_factory=list, description="所有发现的问题")
        error_count: int = Field(default=0, description="error级别问题数")
        warning_count: int = Field(default=0, description="warning级别问题数")
        info_count: int = Field(default=0, description="info级别问题数")
        overall_summary: str = Field(description="整体评审总结")

    data: CodeReviewData = Field(description="代码评审报告数据")


# 保持原有类型定义，兼容流水线完整流程
class ArchitectureDesign(BaseArtifact):
    """架构设计制品"""
    class Component(BaseModel):
        component_id: str = Field(description="组件ID")
        name: str = Field(description="组件名称")
        description: str = Field(description="组件描述")
        type: str = Field(description="组件类型（frontend/backend/service/database）")
        responsibilities: List[str] = Field(default_factory=list, description="职责列表")

    class APIContract(BaseModel):
        contract_id: str = Field(description="契约ID")
        component_from: str = Field(description="调用方组件")
        component_to: str = Field(description="被调用方组件")
        method: str = Field(description="HTTP方法或调用方式")
        path: str = Field(description="路径或接口名")
        request_schema: str = Field(description="请求 schema")
        response_schema: str = Field(description="响应 schema")

    class ArchitectureData(BaseModel):
        title: str = Field(description="架构设计标题")
        description: str = Field(description="架构概述")
        tech_stack: List[Dict[str, str]] = Field(default_factory=list, description="技术选型列表，包含 name, version, reason")
        components: List["Component"] = Field(default_factory=list, description="组件列表")  # noqa: F821
        api_contracts: List["APIContract"] = Field(default_factory=list, description="API契约列表")  # noqa: F821
        dependencies: List[Dict[str, str]] = Field(default_factory=list, description="组件依赖关系")
        architecture_diagram_mermaid: Optional[str] = Field(default=None, description="Mermaid格式架构图")

    data: ArchitectureData = Field(description="架构设计数据")


class UIPrototype(BaseArtifact):
    """UI原型设计制品"""
    class Page(BaseModel):
        page_id: str = Field(description="页面ID")
        name: str = Field(description="页面名称")
        path: str = Field(description="路由路径")
        description: str = Field(description="页面功能描述")
        components: List[str] = Field(default_factory=list, description="页面包含的组件列表")
        interactions: List[str] = Field(default_factory=list, description="交互行为列表")

    class Component(BaseModel):
        component_id: str = Field(description="组件ID")
        name: str = Field(description="组件名称")
        description: str = Field(description="组件功能描述")
        props: List[Dict[str, str]] = Field(default_factory=list, description="属性列表")
        events: List[str] = Field(default_factory=list, description="事件列表")

    class UIPrototypeData(BaseModel):
        title: str = Field(description="UI设计标题")
        description: str = Field(description="UI设计概述")
        layout: str = Field(description="整体布局说明")
        design_system: str = Field(description="设计系统/UI库说明")
        color_scheme: List[Dict[str, str]] = Field(default_factory=list, description="配色方案")
        pages: List["Page"] = Field(default_factory=list, description="页面列表")  # noqa: F821
        components: List["Component"] = Field(default_factory=list, description="可复用组件列表")  # noqa: F821
        navigation_map_mermaid: Optional[str] = Field(default=None, description="Mermaid格式导航结构图")

    data: UIPrototypeData = Field(description="UI原型数据")


class DatabaseSchema(BaseArtifact):
    """数据库设计制品"""
    class Table(BaseModel):
        table_id: str = Field(description="表ID")
        table_name: str = Field(description="表名")
        description: str = Field(description="表描述")
        columns: List[Dict[str, str]] = Field(default_factory=list, description="列定义，包含 name, type, constraints, description")
        primary_key: List[str] = Field(default_factory=list, description="主键列")
        indexes: List[Dict[str, str]] = Field(default_factory=list, description="索引列表")
        foreign_keys: List[Dict[str, str]] = Field(default_factory=list, description="外键定义")

    class DatabaseData(BaseModel):
        title: str = Field(description="数据库设计标题")
        description: str = Field(description="数据库设计概述")
        database_type: str = Field(description="数据库类型")
        tables: List["Table"] = Field(default_factory=list, description="表列表")  # noqa: F821
        relationships: List[Dict[str, str]] = Field(default_factory=list, description="表关系")
        er_diagram_mermaid: Optional[str] = Field(default=None, description="Mermaid格式ER图")
        sql_schema_path: Optional[str] = Field(default=None, description="生成的SQL schema文件路径")

    data: DatabaseData = Field(description="数据库设计数据")


class TaskBacklog(BaseArtifact):
    """任务拆分制品"""
    class TaskItem(BaseModel):
        task_id: str = Field(description="任务ID")
        title: str = Field(description="任务标题")
        description: str = Field(description="任务描述")
        requirement_id: Optional[str] = Field(default=None, description="关联的需求ID")
        component_id: Optional[str] = Field(default=None, description="关联的组件ID")
        priority: str = Field(description="优先级（high/medium/low）")
        estimated_effort: Optional[str] = Field(default=None, description="预估工作量")
        dependencies: List[str] = Field(default_factory=list, description="依赖的任务ID列表")

    class TaskBacklogData(BaseModel):
        title: str = Field(description="任务列表标题")
        description: str = Field(description="任务拆分概述")
        tasks: List["TaskItem"] = Field(default_factory=list, description="任务列表")  # noqa: F821
        total_estimated_effort: Optional[str] = Field(default=None, description="总预估工作量")

    data: TaskBacklogData = Field(description="任务拆分数据")


class CodegenImplementation(BaseArtifact):
    """代码生成制品"""
    class ImplementationNote(BaseModel):
        file_path: str = Field(description="文件路径")
        description: str = Field(description="文件功能描述")
        key_functions: List[str] = Field(default_factory=list, description="关键函数/类列表")

    class CodegenData(BaseModel):
        title: str = Field(description="实现标题")
        description: str = Field(description="实现概述")
        files: List["ImplementationNote"] = Field(default_factory=list, description="生成的文件列表")  # noqa: F821
        notes: str = Field(default="", description="实现说明")

    data: CodegenData = Field(description="代码生成数据")
    base_path: str = Field(description="代码输出根目录")


class TestReport(BaseArtifact):
    """测试验证报告制品"""
    class TestCase(BaseModel):
        test_id: str = Field(description="测试用例ID")
        title: str = Field(description="测试用例标题")
        requirement_id: Optional[str] = Field(default=None, description="关联需求ID")
        type: str = Field(description="测试类型（unit/integration/e2e）")
        expected: str = Field(description="期望结果")
        actual: Optional[str] = Field(default=None, description="实际结果")
        passed: bool = Field(description="是否通过")

    class TestData(BaseModel):
        title: str = Field(description="测试报告标题")
        description: str = Field(description="测试概述")
        test_cases: List["TestCase"] = Field(default_factory=list, description="测试用例列表")  # noqa: F821
        total_count: int = Field(description="总用例数")
        passed_count: int = Field(description="通过数")
        failed_count: int = Field(description="失败数")
        coverage: Optional[float] = Field(default=None, description="覆盖率")
        summary: str = Field(description="总结")
        passed: bool = Field(description="整体是否通过")

    data: TestData = Field(description="测试数据")


class PreReleaseCheck(BaseArtifact):
    """预发布检查制品"""
    class CheckItem(BaseModel):
        check_id: str = Field(description="检查项ID")
        description: str = Field(description="检查项描述")
        result: str = Field(description="检查结果（passed/failed/warning）")
        notes: str = Field(default="", description="备注")

    class PreReleaseData(BaseModel):
        title: str = Field(description="预发布检查标题")
        description: str = Field(description="预发布检查概述")
        checks: List["CheckItem"] = Field(default_factory=list, description="检查项列表")  # noqa: F821
        all_requirements_implemented: bool = Field(description="是否所有需求都已实现")
        consistency_ok: bool = Field(description="设计与实现是否一致")
        summary: str = Field(description="总结")
        passed: bool = Field(description="整体是否通过")

    data: PreReleaseData = Field(description="预发布检查数据")


class DeploymentConfig(BaseArtifact):
    """部署配置制品"""
    class ConfigFile(BaseModel):
        path: str = Field(description="配置文件路径")
        description: str = Field(description="配置文件描述")
        type: str = Field(description="配置文件类型")

    class DeploymentData(BaseModel):
        title: str = Field(description="部署配置标题")
        description: str = Field(description="部署配置概述")
        environment_requirements: List[Dict[str, str]] = Field(default_factory=list, description="环境要求")
        config_files: List["ConfigFile"] = Field(default_factory=list, description="配置文件列表")  # noqa: F821
        deployment_steps: List[str] = Field(default_factory=list, description="部署步骤")
        monitoring_requirements: List[str] = Field(default_factory=list, description="监控需求")
        rollback_steps: List[str] = Field(default_factory=list, description="回滚步骤")
        post_deployment_checks: List[str] = Field(default_factory=list, description="部署后检查项")

    data: DeploymentData = Field(description="部署配置数据")
