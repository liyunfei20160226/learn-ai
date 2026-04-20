"""架构验证器 - 验证生成的JSON符合schema"""
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from utils.file_utils import write_text
from utils.logger import get_logger

logger = get_logger()


# ============ Pydantic Models for JSON Schema ============

class DependencyItem(BaseModel):
    name: str
    version: Optional[str] = None
    description: Optional[str] = None


class TechStackBackend(BaseModel):
    language: Optional[str] = None
    framework: Optional[List[str]] = None
    database: Optional[str] = None
    orm: Optional[str] = None
    authentication: Optional[str] = None


class TechStackFrontend(BaseModel):
    language: Optional[str] = None
    framework: Optional[List[str]] = None
    buildTool: Optional[str] = None
    cssFramework: Optional[str] = None


class TechStack(BaseModel):
    backend: Optional[TechStackBackend] = None
    frontend: Optional[TechStackFrontend] = None
    deployment: Optional[List[str]] = None


class Architecture(BaseModel):
    overview: Optional[str] = None
    architecturePattern: Optional[str] = None
    techStack: Optional[TechStack] = None


class Project(BaseModel):
    name: str
    description: str
    type: Optional[str] = None
    platform: Optional[List[str]] = None


class ModuleFile(BaseModel):
    path: str
    description: Optional[str] = None
    dependencies: Optional[List[str]] = None


class BackendModule(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    directory: Optional[str] = None
    userStoryIds: Optional[List[str]] = None
    files: Optional[List[ModuleFile]] = None
    dependencies: Optional[List[str]] = None


class DataModelField(BaseModel):
    name: str
    type: Optional[str] = None
    constraints: Optional[List[str]] = None
    default: Optional[str] = None
    description: Optional[str] = None


class DataModelRelationship(BaseModel):
    type: str
    targetModel: str
    foreignKey: Optional[str] = None


class DataModel(BaseModel):
    name: str
    description: Optional[str] = None
    tableName: Optional[str] = None
    fields: Optional[List[DataModelField]] = None
    relationships: Optional[List[DataModelRelationship]] = None


class ApiEndpoint(BaseModel):
    id: Optional[str] = None
    method: str
    path: str
    description: Optional[str] = None
    authentication: Optional[bool] = None
    requestBody: Optional[str] = None
    responseFormat: Optional[str] = None
    errorResponses: Optional[List[str]] = None


class DevelopmentConfig(BaseModel):
    setupSteps: Optional[List[str]] = None
    buildCommand: Optional[str] = None
    devCommand: Optional[str] = None
    testCommand: Optional[str] = None
    lintCommand: Optional[str] = None


class BackendSection(BaseModel):
    directoryStructure: Optional[str] = None
    modules: Optional[List[BackendModule]] = None
    dataModels: Optional[List[DataModel]] = None
    apiEndpoints: Optional[List[ApiEndpoint]] = None
    dependencies: Optional[List[DependencyItem]] = None
    development: Optional[DevelopmentConfig] = None


class FrontendApiEndpoint(BaseModel):
    name: str
    method: str
    path: str
    description: Optional[str] = None


class FrontendApiClient(BaseModel):
    baseURL: Optional[str] = None
    endpoints: Optional[List[FrontendApiEndpoint]] = None


class FrontendRoute(BaseModel):
    path: str
    component: Optional[str] = None
    description: Optional[str] = None


class FrontendModule(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    directory: Optional[str] = None
    userStoryIds: Optional[List[str]] = None
    files: Optional[List[ModuleFile]] = None
    dependencies: Optional[List[str]] = None


class FrontendSection(BaseModel):
    directoryStructure: Optional[str] = None
    modules: Optional[List[FrontendModule]] = None
    apiClient: Optional[FrontendApiClient] = None
    routes: Optional[List[FrontendRoute]] = None
    dependencies: Optional[List[DependencyItem]] = None
    development: Optional[DevelopmentConfig] = None


class SharedSection(BaseModel):
    dependencies: Optional[Dict[str, List[DependencyItem]]] = None


class ImplementationStep(BaseModel):
    step: int
    target: str  # backend|frontend|shared
    moduleId: Optional[str] = None
    description: Optional[str] = None
    userStoryIds: Optional[List[str]] = None
    estimatedStories: Optional[int] = None


class Considerations(BaseModel):
    security: Optional[List[str]] = None
    performance: Optional[List[str]] = None
    scalability: Optional[List[str]] = None
    maintainability: Optional[List[str]] = None


class Metadata(BaseModel):
    generatedAt: Optional[str] = None
    sourcePrd: Optional[str] = None
    version: Optional[str] = None


class ArchitectureDocument(BaseModel):
    """完整的架构设计文档JSON schema"""
    project: Project
    architecture: Optional[Architecture] = None
    backend: Optional[BackendSection] = None
    frontend: Optional[FrontendSection] = None
    shared: Optional[SharedSection] = None
    implementationOrder: Optional[List[ImplementationStep]] = None
    considerations: Optional[Considerations] = None
    metadata: Optional[Metadata] = None


def extract_json_from_text(text: str) -> Optional[str]:
    """从AI输出中提取JSON内容

    AI可能用markdown包裹json，比如 ```json ... ```
    """
    # 尝试匹配 ```json 块
    json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_block_match:
        return json_block_match.group(1)

    # 尝试匹配整个文本就是json
    stripped = text.strip()
    if stripped.startswith('{') and stripped.endswith('}'):
        return stripped

    # 尝试找到第一个 { 和最后一个 }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
        return text[first_brace:last_brace + 1]

    return None


def _save_failed_response(
    content: str,
    output_dir: Optional[str],
    attempt: int,
    failure_type: str,
) -> None:
    """保存失败的AI响应到文件用于调试"""
    if not output_dir:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"failed_response_{timestamp}_attempt{attempt}_{failure_type}.txt"
    filepath = os.path.join(output_dir, filename)

    success = write_text(filepath, content)
    if success:
        logger.info(f"完整失败响应已保存到: {filepath}")
    else:
        logger.warning(f"保存失败响应到 {filepath} 失败")


def validate_architecture(
    content: str,
    output_dir: Optional[str] = None,
    attempt: int = 1,
) -> Optional[Dict[str, Any]]:
    """验证架构JSON，返回解析后的dict

    Args:
        content: AI生成的内容（可能包含markdown）
        output_dir: 输出目录，失败时保存完整响应，None不保存
        attempt: 第几次尝试，用于文件名

    Returns:
        验证通过返回dict，否则返回None
    """
    # 提取JSON
    json_str = extract_json_from_text(content)
    if json_str is None:
        logger.error("无法从输出中提取JSON内容")
        _save_failed_response(content, output_dir, attempt, "extraction_failed")
        return None

    # 解析JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        logger.debug(f"JSON内容: {json_str[:500]}...")
        _save_failed_response(content, output_dir, attempt, "json_parse_failed")
        return None

    # 使用pydantic验证schema
    try:
        doc = ArchitectureDocument(**data)
        # 转换回dict返回
        return doc.model_dump()
    except ValidationError as e:
        logger.error(f"Schema验证失败: {e}")
        _save_failed_response(content, output_dir, attempt, "schema_validation_failed")
        return None
    except Exception as e:
        logger.error(f"验证失败: {e}")
        _save_failed_response(content, output_dir, attempt, "validation_failed")
        return None
