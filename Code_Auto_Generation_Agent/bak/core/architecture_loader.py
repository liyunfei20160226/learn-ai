"""架构文档加载器 - 读取和解析architecture.json"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.file_utils import read_json
from utils.logger import get_logger

logger = get_logger()


@dataclass
class Dependency:
    """依赖包"""
    name: str
    version: str
    description: str = ""


@dataclass
class Field:
    """数据模型字段"""
    name: str
    type: str
    constraints: List[str]
    default: Optional[str]
    description: str = ""


@dataclass
class DataModel:
    """数据模型"""
    name: str
    description: str
    table_name: str
    fields: List[Field]
    relationships: List[Any]


@dataclass
class ApiEndpoint:
    """API端点"""
    id: str
    method: str
    path: str
    description: str
    authentication: bool
    request_body: Optional[str]
    response_format: str
    error_responses: List[str]


@dataclass
class ModuleFile:
    """模块文件"""
    path: str
    description: str
    dependencies: List[str]


@dataclass
class Module:
    """模块"""
    id: str
    name: str
    description: str
    directory: str
    user_story_ids: List[str]
    files: List[ModuleFile]
    dependencies: List[str]


@dataclass
class DevelopmentConfig:
    """开发配置"""
    setup_steps: List[str]
    build_command: str
    dev_command: str
    test_command: str
    lint_command: str


@dataclass
class BackendArchitecture:
    """后端架构"""
    directory_structure: str
    modules: List[Module]
    data_models: List[DataModel]
    api_endpoints: List[ApiEndpoint]
    dependencies: List[Dependency]
    development: DevelopmentConfig


@dataclass
class ApiClientEndpoint:
    """API客户端端点"""
    name: str
    method: str
    path: str
    description: str


@dataclass
class ApiClient:
    """API客户端配置"""
    base_url: str
    endpoints: List[ApiClientEndpoint]


@dataclass
class Route:
    """路由配置"""
    path: str
    component: str
    description: str


@dataclass
class FrontendArchitecture:
    """前端架构"""
    directory_structure: str
    modules: List[Module]
    api_client: ApiClient
    routes: List[Route]
    dependencies: List[Dependency]
    dev_dependencies: List[Dependency]
    development: DevelopmentConfig


@dataclass
class ProjectInfo:
    """项目基本信息"""
    name: str
    description: str
    type: str
    platform: List[str]


@dataclass
class TechStack:
    """技术栈"""
    backend: Dict[str, Any]
    frontend: Dict[str, Any]
    deployment: List[str]


@dataclass
class ArchitectureOverview:
    """架构概览"""
    overview: str
    architecture_pattern: str
    tech_stack: TechStack


@dataclass
class ImplementationStep:
    """实现步骤"""
    step: int
    target: str
    module_id: str
    description: str
    user_story_ids: List[str]
    estimated_stories: int


@dataclass
class Considerations:
    """架构注意事项"""
    security: List[str]
    performance: List[str]
    scalability: List[str]
    maintainability: List[str]


@dataclass
class SharedDependencies:
    """共享依赖"""
    python: List[Dependency]
    node: List[Dependency]


@dataclass
class Metadata:
    """元数据"""
    generated_at: str
    source_prd: str
    version: str


@dataclass
class ArchitectureDocument:
    """架构文档"""
    project: ProjectInfo
    architecture: ArchitectureOverview
    backend: BackendArchitecture
    frontend: FrontendArchitecture
    shared: SharedDependencies
    implementation_order: List[ImplementationStep]
    considerations: Considerations
    metadata: Metadata


def _camel_to_snake(name: str) -> str:
    """驼峰命名转蛇形命名"""
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def _dict_to_dataclass(data: Dict[str, Any], dc: Any) -> Any:
    """将字典转换为dataclass实例，自动处理驼峰到蛇形"""
    if data is None:
        return None

    import dataclasses
    fields = {f.name for f in dataclasses.fields(dc)}
    converted = {}
    for key, value in data.items():
        snake_key = _camel_to_snake(key)
        if snake_key in fields:
            converted[snake_key] = value
        elif key in fields:
            converted[key] = value
    return dc(**converted)


def _parse_dependency(dep_data: Any) -> Dependency:
    """解析依赖数据，支持字典和字符串格式"""
    if isinstance(dep_data, dict):
        return Dependency(
            name=dep_data.get('name', ''),
            version=dep_data.get('version', ''),
            description=dep_data.get('description', '')
        )
    elif isinstance(dep_data, str):
        # 处理 "package ^x.y.z" 格式
        parts = dep_data.split(' ', 1)
        if len(parts) >= 2:
            return Dependency(name=parts[0], version=parts[1], description='')
        else:
            return Dependency(name=dep_data, version='', description='')
    return Dependency(name=str(dep_data), version='', description='')


def _parse_dependency_list(deps_data: Any) -> List[Dependency]:
    """解析依赖列表"""
    if not deps_data:
        return []
    if isinstance(deps_data, list):
        return [_parse_dependency(d) for d in deps_data]
    return []


def load_architecture(architecture_path: str) -> Optional[ArchitectureDocument]:
    """加载并解析architecture.json"""
    if not os.path.exists(architecture_path):
        logger.error(f"架构文档不存在: {architecture_path}")
        return None

    data = read_json(architecture_path)
    if data is None:
        logger.error(f"读取架构文档 {architecture_path} 失败")
        return None

    try:
        # 解析 ProjectInfo
        project_data = data.get('project', {})
        project = _dict_to_dataclass(project_data, ProjectInfo)

        # 解析 ArchitectureOverview 和 TechStack
        arch_data = data.get('architecture', {})
        tech_stack_data = arch_data.get('techStack', arch_data.get('tech_stack', {}))
        tech_stack = TechStack(
            backend=tech_stack_data.get('backend', {}),
            frontend=tech_stack_data.get('frontend', {}),
            deployment=tech_stack_data.get('deployment', [])
        )
        architecture_overview = ArchitectureOverview(
            overview=arch_data.get('overview', ''),
            architecture_pattern=arch_data.get('architecturePattern', arch_data.get('architecture_pattern', '')),
            tech_stack=tech_stack
        )

        # 解析 BackendArchitecture
        backend_data = data.get('backend', {})

        backend_modules = []
        for mod_data in backend_data.get('modules', []):
            files = []
            for f_data in mod_data.get('files', []):
                files.append(ModuleFile(
                    path=f_data.get('path', ''),
                    description=f_data.get('description', ''),
                    dependencies=f_data.get('dependencies', [])
                ))
            backend_modules.append(Module(
                id=mod_data.get('id', ''),
                name=mod_data.get('name', ''),
                description=mod_data.get('description', ''),
                directory=mod_data.get('directory', ''),
                user_story_ids=mod_data.get('userStoryIds', mod_data.get('user_story_ids', [])),
                files=files,
                dependencies=mod_data.get('dependencies', [])
            ))

        backend_data_models = []
        for dm_data in backend_data.get('dataModels', backend_data.get('data_models', [])):
            fields = []
            for f_data in dm_data.get('fields', []):
                fields.append(Field(
                    name=f_data.get('name', ''),
                    type=f_data.get('type', ''),
                    constraints=f_data.get('constraints', []),
                    default=f_data.get('default'),
                    description=f_data.get('description', '')
                ))
            backend_data_models.append(DataModel(
                name=dm_data.get('name', ''),
                description=dm_data.get('description', ''),
                table_name=dm_data.get('tableName', dm_data.get('table_name', '')),
                fields=fields,
                relationships=dm_data.get('relationships', [])
            ))

        backend_api_endpoints = []
        for ep_data in backend_data.get('apiEndpoints', backend_data.get('api_endpoints', [])):
            backend_api_endpoints.append(ApiEndpoint(
                id=ep_data.get('id', ''),
                method=ep_data.get('method', ''),
                path=ep_data.get('path', ''),
                description=ep_data.get('description', ''),
                authentication=ep_data.get('authentication', False),
                request_body=ep_data.get('requestBody', ep_data.get('request_body')),
                response_format=ep_data.get('responseFormat', ep_data.get('response_format', 'application/json')),
                error_responses=ep_data.get('errorResponses', ep_data.get('error_responses', []))
            ))

        backend_dependencies = _parse_dependency_list(backend_data.get('dependencies', []))

        backend_dev_data = backend_data.get('development', {})
        backend_development = DevelopmentConfig(
            setup_steps=backend_dev_data.get('setupSteps', backend_dev_data.get('setup_steps', [])),
            build_command=backend_dev_data.get('buildCommand', backend_dev_data.get('build_command', '')),
            dev_command=backend_dev_data.get('devCommand', backend_dev_data.get('dev_command', '')),
            test_command=backend_dev_data.get('testCommand', backend_dev_data.get('test_command', '')),
            lint_command=backend_dev_data.get('lintCommand', backend_dev_data.get('lint_command', ''))
        )

        backend = BackendArchitecture(
            directory_structure=backend_data.get('directoryStructure', backend_data.get('directory_structure', '')),
            modules=backend_modules,
            data_models=backend_data_models,
            api_endpoints=backend_api_endpoints,
            dependencies=backend_dependencies,
            development=backend_development
        )

        # 解析 FrontendArchitecture
        frontend_data = data.get('frontend', {})

        frontend_modules = []
        for mod_data in frontend_data.get('modules', []):
            files = []
            for f_data in mod_data.get('files', []):
                files.append(ModuleFile(
                    path=f_data.get('path', ''),
                    description=f_data.get('description', ''),
                    dependencies=f_data.get('dependencies', [])
                ))
            frontend_modules.append(Module(
                id=mod_data.get('id', ''),
                name=mod_data.get('name', ''),
                description=mod_data.get('description', ''),
                directory=mod_data.get('directory', ''),
                user_story_ids=mod_data.get('userStoryIds', mod_data.get('user_story_ids', [])),
                files=files,
                dependencies=mod_data.get('dependencies', [])
            ))

        api_client_data = frontend_data.get('apiClient', frontend_data.get('api_client', {}))
        api_client_endpoints = []
        for ep_data in api_client_data.get('endpoints', []):
            api_client_endpoints.append(ApiClientEndpoint(
                name=ep_data.get('name', ''),
                method=ep_data.get('method', ''),
                path=ep_data.get('path', ''),
                description=ep_data.get('description', '')
            ))
        api_client = ApiClient(
            base_url=api_client_data.get('baseUrl', api_client_data.get('base_url', '')),
            endpoints=api_client_endpoints
        )

        routes = []
        for r_data in frontend_data.get('routes', []):
            routes.append(Route(
                path=r_data.get('path', ''),
                component=r_data.get('component', ''),
                description=r_data.get('description', '')
            ))

        frontend_dependencies = _parse_dependency_list(frontend_data.get('dependencies', []))
        frontend_dev_dependencies = _parse_dependency_list(frontend_data.get('devDependencies', frontend_data.get('dev_dependencies', [])))

        frontend_dev_data = frontend_data.get('development', {})
        frontend_development = DevelopmentConfig(
            setup_steps=frontend_dev_data.get('setupSteps', frontend_dev_data.get('setup_steps', [])),
            build_command=frontend_dev_data.get('buildCommand', frontend_dev_data.get('build_command', '')),
            dev_command=frontend_dev_data.get('devCommand', frontend_dev_data.get('dev_command', '')),
            test_command=frontend_dev_data.get('testCommand', frontend_dev_data.get('test_command', '')),
            lint_command=frontend_dev_data.get('lintCommand', frontend_dev_data.get('lint_command', ''))
        )

        frontend = FrontendArchitecture(
            directory_structure=frontend_data.get('directoryStructure', frontend_data.get('directory_structure', '')),
            modules=frontend_modules,
            api_client=api_client,
            routes=routes,
            dependencies=frontend_dependencies,
            dev_dependencies=frontend_dev_dependencies,
            development=frontend_development
        )

        # 解析 SharedDependencies
        shared_data = data.get('shared', {})
        shared = SharedDependencies(
            python=_parse_dependency_list(shared_data.get('python', [])),
            node=_parse_dependency_list(shared_data.get('node', []))
        )

        # 解析 ImplementationOrder
        implementation_order = []
        for step_data in data.get('implementationOrder', data.get('implementation_order', [])):
            implementation_order.append(ImplementationStep(
                step=step_data.get('step', 0),
                target=step_data.get('target', ''),
                module_id=step_data.get('moduleId', step_data.get('module_id', '')),
                description=step_data.get('description', ''),
                user_story_ids=step_data.get('userStoryIds', step_data.get('user_story_ids', [])),
                estimated_stories=step_data.get('estimatedStories', step_data.get('estimated_stories', 0))
            ))

        # 解析 Considerations
        considerations_data = data.get('considerations', {})
        considerations = Considerations(
            security=considerations_data.get('security', []),
            performance=considerations_data.get('performance', []),
            scalability=considerations_data.get('scalability', []),
            maintainability=considerations_data.get('maintainability', [])
        )

        # 解析 Metadata
        metadata_data = data.get('metadata', {})
        metadata = Metadata(
            generated_at=metadata_data.get('generatedAt', metadata_data.get('generated_at', '')),
            source_prd=metadata_data.get('sourcePrd', metadata_data.get('source_prd', '')),
            version=metadata_data.get('version', '')
        )

        arch_doc = ArchitectureDocument(
            project=project,
            architecture=architecture_overview,
            backend=backend,
            frontend=frontend,
            shared=shared,
            implementation_order=implementation_order,
            considerations=considerations,
            metadata=metadata
        )

        logger.info(f"已加载架构文档: {arch_doc.project.name}")
        logger.info(f"  - 后端模块: {len(arch_doc.backend.modules)} 个")
        logger.info(f"  - 前端模块: {len(arch_doc.frontend.modules)} 个")
        logger.info(f"  - 数据模型: {len(arch_doc.backend.data_models)} 个")
        logger.info(f"  - API端点: {len(arch_doc.backend.api_endpoints)} 个")

        return arch_doc

    except Exception as e:
        logger.error(f"解析架构文档失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def format_architecture_for_ai(arch: ArchitectureDocument) -> str:
    """将架构文档格式化为AI易读的文本格式"""
    lines = []

    # 项目基本信息
    lines.append("## 项目基本信息")
    lines.append(f"- 项目名称: {arch.project.name}")
    lines.append(f"- 项目描述: {arch.project.description}")
    lines.append(f"- 项目类型: {arch.project.type}")
    lines.append(f"- 目标平台: {', '.join(arch.project.platform)}")
    lines.append("")

    # 架构概览
    lines.append("## 架构概览")
    lines.append(f"- 架构模式: {arch.architecture.architecture_pattern}")
    lines.append(f"- 概述: {arch.architecture.overview}")
    lines.append("")

    # 技术栈
    lines.append("## 技术栈")
    lines.append("### 后端")
    backend_stack = arch.architecture.tech_stack.backend
    for key, value in backend_stack.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("### 前端")
    frontend_stack = arch.architecture.tech_stack.frontend
    for key, value in frontend_stack.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append(f"### 部署: {', '.join(arch.architecture.tech_stack.deployment)}")
    lines.append("")

    # 后端目录结构
    lines.append("## 后端目录结构")
    lines.append("```")
    lines.append(arch.backend.directory_structure)
    lines.append("```")
    lines.append("")

    # 后端依赖
    lines.append("## 后端依赖")
    for dep in arch.backend.dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
        if dep.description:
            lines.append(f"  说明: {dep.description}")
    lines.append("")

    # 数据模型
    lines.append("## 数据模型")
    for model in arch.backend.data_models:
        lines.append(f"### {model.name}")
        lines.append(f"- 描述: {model.description}")
        lines.append(f"- 表名/存储: {model.table_name}")
        lines.append("- 字段:")
        for field in model.fields:
            constraints = ", ".join(field.constraints)
            default_str = f" = {field.default}" if field.default else ""
            lines.append(f"  - {field.name}: {field.type} [{constraints}]{default_str}")
            if field.description:
                lines.append(f"    说明: {field.description}")
        lines.append("")

    # API端点
    lines.append("## API端点")
    for ep in arch.backend.api_endpoints:
        auth_str = "需要认证" if ep.authentication else "无需认证"
        lines.append(f"- [{ep.id}] {ep.method} {ep.path}")
        lines.append(f"  描述: {ep.description}")
        lines.append(f"  认证: {auth_str}")
        if ep.request_body:
            lines.append(f"  请求体: {ep.request_body}")
        lines.append(f"  响应格式: {ep.response_format}")
    lines.append("")

    # 前端目录结构
    lines.append("## 前端目录结构")
    lines.append("```")
    lines.append(arch.frontend.directory_structure)
    lines.append("```")
    lines.append("")

    # 前端依赖
    lines.append("## 前端依赖")
    lines.append("### 生产依赖")
    for dep in arch.frontend.dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
    lines.append("")

    lines.append("### 开发依赖")
    for dep in arch.frontend.dev_dependencies:
        if dep.version:
            lines.append(f"- {dep.name} {dep.version}")
        else:
            lines.append(f"- {dep.name}")
    lines.append("")

    # 开发配置
    lines.append("## 开发配置")
    lines.append("### 后端")
    lines.append(f"- 构建命令: {arch.backend.development.build_command}")
    lines.append(f"- 开发命令: {arch.backend.development.dev_command}")
    lines.append(f"- 测试命令: {arch.backend.development.test_command}")
    lines.append(f"- Lint命令: {arch.backend.development.lint_command}")
    lines.append("")

    lines.append("### 前端")
    lines.append(f"- 构建命令: {arch.frontend.development.build_command}")
    lines.append(f"- 开发命令: {arch.frontend.development.dev_command}")
    lines.append(f"- 测试命令: {arch.frontend.development.test_command}")
    lines.append(f"- Lint命令: {arch.frontend.development.lint_command}")

    return "\n".join(lines)


def format_architecture_context_for_story(arch: ArchitectureDocument) -> str:
    """为用户故事提示词生成精简的架构上下文"""
    lines = []
    lines.append("=== 项目架构上下文 ===")
    lines.append("")

    # 技术栈（精简版）
    lines.append("技术栈:")
    backend_stack = arch.architecture.tech_stack.backend
    frontend_stack = arch.architecture.tech_stack.frontend

    backend_lang = backend_stack.get('language', '未知')
    backend_framework = ', '.join(backend_stack.get('framework', []))
    frontend_lang = frontend_stack.get('language', '未知')
    frontend_framework = ', '.join(frontend_stack.get('framework', []))

    lines.append(f"- 后端: {backend_lang} + {backend_framework}")
    lines.append(f"- 前端: {frontend_lang} + {frontend_framework}")
    lines.append(f"- 部署: {', '.join(arch.architecture.tech_stack.deployment)}")
    lines.append("")

    # 关键依赖版本（用于修复时的正确决策）
    lines.append("关键依赖版本（重要！修复错误时请使用正确的版本兼容格式）:")
    lines.append("后端依赖:")
    for dep in arch.backend.dependencies[:10]:  # 只显示前10个
        if dep.version:
            lines.append(f"- {dep.name}: {dep.version}")
        else:
            lines.append(f"- {dep.name}")

    lines.append("")
    lines.append("前端依赖:")
    all_frontend_deps = arch.frontend.dependencies + arch.frontend.dev_dependencies
    for dep in all_frontend_deps[:20]:  # 只显示前20个，包含生产和开发依赖
        if dep.version:
            lines.append(f"- {dep.name}: {dep.version}")
        else:
            lines.append(f"- {dep.name}")

    lines.append("")

    # ESLint 特别提醒（同时检查 dependencies 和 dev_dependencies）
    eslint_version = None
    all_frontend_deps = arch.frontend.dependencies + arch.frontend.dev_dependencies
    for dep in all_frontend_deps:
        if dep.name.lower() == 'eslint':
            eslint_version = dep.version
            break

    if eslint_version:
        # 处理版本号前缀，如 ^8.57.1, ~8, >=8 等
        version_clean = eslint_version.lstrip('^~>=<')
        major_version = int(version_clean.split('.')[0]) if '.' in version_clean else int(version_clean) if version_clean.isdigit() else 8
        lines.append("ESLint 版本特别提醒:")
        lines.append(f"- 当前项目 ESLint 版本: {eslint_version}")
        if major_version < 9:
            lines.append("- 配置文件格式: 使用 .eslintrc.js (CommonJS 格式)")
            lines.append("- 不要使用 eslint.config.js 新格式 (ESLint 9+)")
        else:
            lines.append("- 配置文件格式: 使用 eslint.config.js (ESLint 9+ 新格式)")
        lines.append("")

    # 目录结构（精简显示）
    lines.append("后端目录结构:")
    lines.append("```")
    lines.append(arch.backend.directory_structure)
    lines.append("```")
    lines.append("")

    lines.append("前端目录结构:")
    lines.append("```")
    lines.append(arch.frontend.directory_structure)
    lines.append("```")
    lines.append("")

    # 数据模型（精简）
    lines.append("数据模型定义:")
    for model in arch.backend.data_models:
        lines.append(f"- {model.name}: {', '.join(f'{f.name}({f.type})' for f in model.fields)}")
    lines.append("")

    # API端点（精简）
    lines.append("API端点概览:")
    for ep in arch.backend.api_endpoints:
        lines.append(f"- {ep.method} {ep.path} - {ep.description}")
    lines.append("")

    lines.append("注意: 请在上述目录结构中创建/修改文件，保持项目结构一致性。")
    lines.append("修复错误时，请确保配置文件格式与依赖版本兼容！")
    lines.append("=== 架构上下文结束 ===")

    return "\n".join(lines)
