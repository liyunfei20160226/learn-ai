"""代码生成协调器 - 精简版本

职责（单一职责原则）：
1. 加载 PRD + Architecture
2. 调用 PlanningAgent 生成任务图
3. 拓扑排序任务（依赖解析）
4. 按顺序调度 CodegenAgent 生成代码
5. 调用 QualityFixOrchestrator 进行质量检查+自动修复
6. 持久化 manifest

注意：快照管理、多轮修复闭环等细节已下沉到子模块
"""

import json
import logging
import traceback
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI

from prompts import PromptTemplate, get_prompt_loader

from .agents.codegen_agent import CodegenAgent
from .agents.planning_agent import PlanningAgent
from .config import AgentConfig, get_config
from .manifest import Manifest, TaskFile
from .quality_fix_orchestrator import QualityFixOrchestrator
from .snapshot_manager import _iter_all_files
from .utils import safe_resolve_path

logger = logging.getLogger(__name__)

# 缓存大小限制 - 防止内存泄漏
_MAX_CACHE_SIZE = 100


class CodegenCoordinator:
    """代码生成协调器（精简版本）

    只负责主流程编排，细节下沉到子模块：
    - SnapshotManager: 快照管理
    - QualityFixOrchestrator: 质量检查+多轮修复
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None,
                 working_dir: str = None, config: AgentConfig = None):
        self.config = config or get_config()

        # 优先级：参数 > 配置 > 默认值
        self.api_key = api_key or self.config.openai_api_key
        self.base_url = base_url or self.config.openai_base_url
        self.model = model or self.config.openai_model

        self.working_dir = Path(working_dir or self.config.working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        llm_kwargs = {
            "model": self.model,
            "api_key": self.api_key,
            "temperature": self.config.openai_temperature,
        }
        if self.base_url:
            llm_kwargs["base_url"] = self.base_url
        if self.config.openai_timeout:
            llm_kwargs["timeout"] = self.config.openai_timeout
        if self.config.openai_max_retries:
            llm_kwargs["max_retries"] = self.config.openai_max_retries

        self.llm = ChatOpenAI(**llm_kwargs)

        self.manifest: Optional[Manifest] = None
        self.prompt_loader = get_prompt_loader(self.config.prompts_dir)
        self.generated_code_cache: OrderedDict[str, List[Dict[str, str]]] = OrderedDict()

    @staticmethod
    def _require_field(data: Dict, field: str, context: str) -> str:
        """要求字段必须存在，无默认值，缺失直接报错。

        这是 Coordinator 与 Architecture Agent 之间的显式契约。
        """
        if data is None or field not in data:
            raise ValueError(
                f"架构文档缺少必填字段: {context}.{field}。\n"
                f"请更新架构设计 JSON，明确定义所有技术栈字段，不允许默认值兜底。"
            )
        return data[field]

    def _topological_sort(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Kahn 算法：拓扑排序

        检测两种异常：
        1. 依赖不存在的任务 ID → 直接报错
        2. 循环依赖 → 任务数量不一致时报错
        """
        task_map = {t["id"]: t for t in tasks}
        task_ids = set(task_map.keys())
        in_degree = {t["id"]: len(t.get("dependencies", [])) for t in tasks}
        adj_list = {t["id"]: [] for t in tasks}

        for task in tasks:
            for dep in task.get("dependencies", []):
                if dep not in task_ids:
                    raise ValueError(
                        f"任务 {task['id']} 依赖不存在的任务 {dep}。\n"
                        f"有效任务 ID: {sorted(task_ids)}"
                    )
                adj_list[dep].append(task["id"])

        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        sorted_tasks = []

        while queue:
            task_id = queue.popleft()
            sorted_tasks.append(task_map[task_id])

            for next_id in adj_list[task_id]:
                in_degree[next_id] -= 1
                if in_degree[next_id] == 0:
                    queue.append(next_id)

        if len(sorted_tasks) != len(tasks):
            unresolved = task_ids - {t["id"] for t in sorted_tasks}
            raise ValueError(
                f"任务图存在循环依赖，无法解析以下任务: {sorted(unresolved)}"
            )

        return sorted_tasks

    def _collect_dependency_code(self, dependencies: List[str]) -> str:
        """收集依赖任务的完整代码（用于上下文注入）"""
        if not dependencies:
            return ""

        sections = []
        for dep_id in dependencies:
            if dep_id in self.generated_code_cache:
                # LRU: 将访问的元素移到末尾（表示最近使用）
                self.generated_code_cache.move_to_end(dep_id)
                files = self.generated_code_cache[dep_id]
                sections.append(f"=== 依赖任务 {dep_id} 已生成代码 ===")
                for f in files:
                    file_path = safe_resolve_path(self.working_dir, f["file_path"])
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as fp:
                            content = fp.read()
                        sections.append(f"--- {f['file_path']} ---")
                        sections.append(content)
                        sections.append("")
            else:
                sections.append(f"⚠️  依赖任务 {dep_id} 未完成，代码不可用")

        return "\n".join(sections)

    def _filter_architecture_docs(self, task_type: str, arch_doc: Dict) -> str:
        """智能过滤架构文档，只注入最相关的内容。

        所有字段必须在架构文档中明确定义，无默认值兜底。
        """
        sections = []
        backend = arch_doc.get("backend")
        frontend = arch_doc.get("frontend")

        _require = self._require_field

        if task_type == "backend":
            sections.append("=== 后端技术栈 ===")
            sections.append(f"- 框架: {_require(backend, 'framework', 'backend')}")
            sections.append(f"- 数据库: {_require(backend, 'database', 'backend')}")
            sections.append(f"- ORM: {_require(backend, 'orm', 'backend')}")
            sections.append(f"- 目录结构:\n{_require(backend, 'directory_structure', 'backend')}")

        elif task_type == "frontend":
            sections.append("=== 前端技术栈 ===")
            sections.append(f"- 框架: {_require(frontend, 'framework', 'frontend')}")
            sections.append(f"- 状态管理: {_require(frontend, 'state_management', 'frontend')}")
            sections.append(f"- UI 库: {_require(frontend, 'ui_library', 'frontend')}")
            sections.append(f"- 目录结构:\n{_require(frontend, 'directory_structure', 'frontend')}")

        elif task_type == "database":
            sections.append("=== 数据库技术栈 ===")
            sections.append(f"- 数据库: {_require(backend, 'database', 'backend')}")
            sections.append(f"- 迁移工具: {_require(backend, 'migration', 'backend')}")

        elif task_type == "shared":
            sections.append("=== 后端技术栈 ===")
            sections.append(f"- 框架: {_require(backend, 'framework', 'backend')}")
            sections.append(f"- 数据库: {_require(backend, 'database', 'backend')}")
            sections.append("=== 前端技术栈 ===")
            sections.append(f"- 框架: {_require(frontend, 'framework', 'frontend')}")

        elif task_type == "infrastructure":
            architecture = arch_doc.get("architecture", {})
            sections.append("=== 基础设施架构 ===")
            sections.append(f"- 部署方式: {architecture.get('deployment', '未指定')}")
            sections.append(f"- 容器化: {architecture.get('containerization', '未指定')}")

        else:
            sections.append("=== 技术栈信息（通用） ===")
            if backend:
                sections.append(f"- 后端框架: {backend.get('framework', '未指定')}")
            if frontend:
                sections.append(f"- 前端框架: {frontend.get('framework', '未指定')}")

        return "\n".join(sections)

    def _save_manifest(self) -> None:
        """保存 manifest 状态（原子写入，委托给 Manifest.save）"""
        manifest_path = self.working_dir / ".codegen_manifest.json"
        self.manifest.save(manifest_path)

    def _load_manifest(self) -> Optional[Manifest]:
        """从工作目录加载已有 manifest（用于断点恢复）"""
        manifest_path = self.working_dir / ".codegen_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return Manifest.from_json(f.read())
        return None

    def process_codegen(
        self,
        prd_path: str,
        architecture_path: str,
        max_stories: int = None,
        dry_run: bool = False,
        progress_callback: Callable = None,
    ) -> Dict:
        """主流程：PRD → 任务规划 → 代码生成 → 质量检查 → 自动修复

        Args:
            prd_path: PRD JSON 文件路径
            architecture_path: 架构设计 JSON 文件路径
            max_stories: 最大生成故事数（用于分批次生成）
            dry_run: 是否只规划不生成
            progress_callback: 进度回调函数

        Returns:
            执行结果统计
        """
        # ========== 阶段 1: 加载输入 ==========
        with open(prd_path, "r", encoding="utf-8") as f:
            prd = json.load(f)

        with open(architecture_path, "r", encoding="utf-8") as f:
            arch = json.load(f)

        # 断点恢复：加载已有 manifest
        self.manifest = self._load_manifest()
        if self.manifest is None:
            self.manifest = Manifest(
                prd_name=prd.get("name", "unknown"),
                working_dir=str(self.working_dir),
            )
            self._save_manifest()

        # ========== 阶段 2: 任务规划 ==========
        if not self.manifest.tasks:
            print("\n🎯 开始任务规划...")
            logger.info("开始任务规划")
            planning_agent = PlanningAgent(self.llm, str(self.working_dir), self.config)
            tasks_result = planning_agent.run_with_log(
                prd_desc=json.dumps(prd, ensure_ascii=False, indent=2),
                architecture_desc=json.dumps(arch, ensure_ascii=False, indent=2),
            )
            self.manifest.tasks = tasks_result["tasks"]
            self._save_manifest()
            print(f"✅ 规划完成，共 {len(self.manifest.tasks)} 个任务")
            logger.info(f"任务规划完成，共 {len(self.manifest.tasks)} 个任务")
        else:
            print(f"\n✅ 从断点恢复，已有 {len(self.manifest.tasks)} 个任务")
            logger.info(f"从断点恢复，已有 {len(self.manifest.tasks)} 个任务")

        if dry_run:
            return {
                "total_tasks": len(self.manifest.tasks),
                "completed_tasks": self.manifest.completed_tasks,
                "status": "dry_run",
            }

        # ========== 阶段 3: 拓扑排序 ==========
        all_tasks = list(self.manifest.tasks.values())
        sorted_tasks = self._topological_sort(all_tasks)

        # 过滤已完成的任务
        pending_sorted = [
            t for t in sorted_tasks
            if t["id"] not in self.manifest.completed_tasks
        ]

        if max_stories:
            pending_sorted = pending_sorted[:max_stories]

        print(f"\n🚀 开始执行 {len(pending_sorted)} 个任务\n")

        # ========== 阶段 4: 逐个任务代码生成 ==========
        for idx, task in enumerate(pending_sorted):
            task_id = task["id"]
            task_name = task["title"]
            task_type = task.get("type", "general")

            print(f"{'='*60}")
            print(f"[{idx+1}/{len(pending_sorted)}] 🔨 {task_id}: {task_name}")
            print(f"{'='*60}")

            # 检查所有依赖是否都成功完成
            dependencies = task.get("dependencies", [])
            failed_deps = []
            for dep_id in dependencies:
                if not self.manifest.is_task_completed(dep_id):
                    failed_deps.append(dep_id)

            if failed_deps:
                print(f"⏭️  跳过任务: 依赖任务未成功完成: {', '.join(failed_deps)}")
                continue

            self.manifest.start_task(task_id)
            self._save_manifest()

            try:
                dep_code = self._collect_dependency_code(task.get("dependencies", []))
                filtered_arch = self._filter_architecture_docs(task_type, arch)

                template: PromptTemplate = self.prompt_loader.load("codegen_task")
                prompt = template.render(
                    task_id=task_id,
                    task_name=task_name,
                    task_description=task.get("description", ""),
                    task_type=task_type,
                    filtered_arch=filtered_arch,
                    dep_code=dep_code or "无前置依赖",
                )

                codegen_agent = CodegenAgent(self.llm, str(self.working_dir), self.config)
                generated_files = codegen_agent.run_with_log(prompt, verbose=True)

                task_files = [TaskFile(**f) for f in generated_files]

                self.manifest.complete_task(task_id, task_files)

                # LRU 缓存：超过容量时淘汰最旧的条目
                self.generated_code_cache[task_id] = generated_files
                if len(self.generated_code_cache) > _MAX_CACHE_SIZE:
                    self.generated_code_cache.popitem(last=False)

                self._save_manifest()

                print(f"✅ 生成完成，共 {len(generated_files)} 个文件")
                for file_info in generated_files:
                    print(f"   - {file_info['file_path']}")  # type: ignore[index]
                print()

            except Exception as e:
                tb_str = traceback.format_exc()
                error_msg = f"{type(e).__name__}: {e}\n{tb_str}"
                self.manifest.fail_task(task_id, error_msg)
                self._save_manifest()
                print(f"❌ 任务 {task_id} 失败: {type(e).__name__}: {e}")
                continue

        # ========== 阶段 5: 质量检查 + 自动修复（委托给子模块） ==========
        print("\n" + "="*60)
        print("🔍 开始质量检查 + 自动修复流程")
        print("="*60)

        # 根据实际存在的字段动态生成技术栈描述
        tech_stack_parts = []
        if "backend" in arch:
            tech_stack_parts.append(f"Backend: {self._require_field(arch['backend'], 'framework', 'backend')}")
        if "frontend" in arch:
            tech_stack_parts.append(f"Frontend: {self._require_field(arch['frontend'], 'framework', 'frontend')}")

        if not tech_stack_parts:
            raise ValueError(
                "架构文档必须包含 backend 或 frontend 字段。\n"
                "纯后端项目只需要 backend，纯前端项目只需要 frontend。"
            )

        tech_stack_desc = "\n".join(tech_stack_parts)

        # 收集项目文件列表（包括隐藏文件！_iter_all_files 已经处理了 ignore 逻辑）
        project_files = [
            str(p.relative_to(self.working_dir))
            for p in _iter_all_files(self.working_dir)
        ]
        project_tree = "\n".join(project_files) if project_files else "(空项目目录)"

        # 委托给 QualityFixOrchestrator 执行质量检查 + 多轮修复
        fix_orchestrator = QualityFixOrchestrator(
            llm=self.llm,
            working_dir=self.working_dir,
            config=self.config,
            manifest=self.manifest,
            prompts_dir=self.config.prompts_dir,
        )

        # 检查是否有实际的命令生成
        commands = fix_orchestrator.prepare_check_commands(tech_stack_desc, project_tree)
        print("📋 检查命令:")
        has_commands = any(cmds for cmds in commands.values())

        if not has_commands:
            print("   ⚠️  未能生成检查命令，跳过质量检查")
            return {
                "session_id": self.manifest.session_id,
                "total_tasks": self.manifest.total_tasks,
                "completed_tasks": self.manifest.completed_tasks,
                "success": True,
                "note": "质量检查被跳过（未生成检查命令）",
            }

        for step_name, cmds in commands.items():
            if cmds:
                cmd_str = ", ".join(cmds[:2])
                if len(cmds) > 2:
                    cmd_str += f" (+{len(cmds)-2} more)"
                print(f"   - {step_name}: {cmd_str}")

        print()

        # 运行完整的自动修复流程
        fix_result = fix_orchestrator.run_auto_fix_loop(
            tech_stack_desc=tech_stack_desc,
            project_tree=project_tree,
            progress_callback=progress_callback,
        )

        return {
            "session_id": self.manifest.session_id,
            "total_tasks": self.manifest.total_tasks,
            "completed_tasks": self.manifest.completed_tasks,
            "success": fix_result["status"] in ("success", "partial_success"),
            "quality_fix": fix_result,
        }
