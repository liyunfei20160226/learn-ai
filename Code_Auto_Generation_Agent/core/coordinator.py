import json
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI

from .codegen_agent import CodegenAgent
from .config import AgentConfig, get_config
from .fix_agent import FixAgent
from .manifest import Manifest, TaskFile
from .planning_agent import PlanningAgent
from .quality_checker import QualityChecker


class CodegenCoordinator:
    """代码生成协调器

    职责：
    1. 加载 PRD + Architecture
    2. 调用 PlanningAgent 生成任务图
    3. 拓扑排序任务
    4. 按顺序调度 CodegenAgent
    5. 管理代码缓存
    6. 调用 QualityChecker 质量检查
    7. 调用 FixAgent 修复错误
    8. 持久化 manifest
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
        self.generated_code_cache: Dict[str, List[Dict[str, str]]] = {}

    def _topological_sort(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Kahn 算法：拓扑排序"""
        task_map = {t["id"]: t for t in tasks}
        in_degree = {t["id"]: len(t.get("dependencies", [])) for t in tasks}
        adj_list = {t["id"]: [] for t in tasks}

        for task in tasks:
            for dep in task.get("dependencies", []):
                if dep in adj_list:
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
            raise ValueError("任务图存在循环依赖")

        return sorted_tasks

    def _collect_dependency_code(self, dependencies: List[str]) -> str:
        """收集依赖任务的完整代码"""
        if not dependencies:
            return ""

        sections = []
        for dep_id in dependencies:
            if dep_id in self.generated_code_cache:
                files = self.generated_code_cache[dep_id]
                sections.append(f"=== 依赖任务 {dep_id} 已生成代码 ===")
                for f in files:
                    file_path = self.working_dir / f["file_path"]
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as fp:
                            content = fp.read()
                        sections.append(f"--- {f['file_path']} ---")
                        sections.append(content)
                        sections.append("")

        return "\n".join(sections)

    def _filter_architecture_docs(self, task_type: str, arch_doc: Dict) -> str:
        """智能过滤架构文档，只注入最相关的内容"""
        sections = []

        if task_type == "backend":
            backend = arch_doc.get("backend", {})
            sections.append("=== 后端技术栈 ===")
            sections.append(f"- 框架: {backend.get('framework', 'FastAPI')}")
            sections.append(f"- 数据库: {backend.get('database', 'SQLite')}")
            sections.append(f"- ORM: {backend.get('orm', 'SQLAlchemy')}")
            sections.append(f"- 目录结构:\n{backend.get('directory_structure', '')}")

        elif task_type == "frontend":
            frontend = arch_doc.get("frontend", {})
            sections.append("=== 前端技术栈 ===")
            sections.append(f"- 框架: {frontend.get('framework', 'React')}")
            sections.append(f"- 状态管理: {frontend.get('state_management', 'Zustand')}")
            sections.append(f"- UI 库: {frontend.get('ui_library', 'Tailwind CSS')}")
            sections.append(f"- 目录结构:\n{frontend.get('directory_structure', '')}")

        return "\n".join(sections)

    def _load_json_file(self, path: str) -> Dict:
        """加载 JSON 文件"""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_manifest(self):
        """保存 Manifest"""
        if self.manifest:
            self.manifest.save(self.working_dir / "manifest.json")

    def process_codegen(
        self,
        prd_path: str,
        architecture_path: str,
        max_stories: int = None,
        dry_run: bool = False,
        progress_callback: Callable = None,
    ) -> Dict:
        """主流程"""
        prd = self._load_json_file(prd_path)
        arch = self._load_json_file(architecture_path)

        manifest_path = self.working_dir / "manifest.json"
        if manifest_path.exists():
            self.manifest = Manifest.load(manifest_path)
            print(f"⏯️  找到已有会话，断点恢复: {self.manifest.session_id}")
        else:
            self.manifest = Manifest.create(project_name=prd.get("name", "Untitled"))

        if not self.manifest.get_pending_tasks():
            print("📋 开始规划任务...")
            planning_agent = PlanningAgent(self.llm, str(self.working_dir), self.config)
            tasks = planning_agent.run_and_parse(
                json.dumps(prd, ensure_ascii=False),
                json.dumps(arch, ensure_ascii=False),
                verbose=True,
            )

            for task in tasks:
                self.manifest.add_task(
                    task["id"],
                    task["title"],
                    task["type"],
                    task.get("dependencies", []),
                )
            self._save_manifest()
            print(f"✅ 规划完成，共 {len(tasks)} 个任务")
        else:
            print(f"📋 已有 {len(self.manifest.tasks)} 个任务")

        pending_tasks = self.manifest.get_pending_tasks()
        all_tasks = [
            {"id": tid, **{k: v for k, v in self.manifest.tasks[tid].__dict__.items() if k != "id"}}
            for tid in self.manifest.tasks
        ]
        sorted_tasks = self._topological_sort(all_tasks)

        pending_sorted = [t for t in sorted_tasks if t["id"] in pending_tasks]

        if max_stories:
            pending_sorted = pending_sorted[:max_stories]

        print(f"🚀 开始执行 {len(pending_sorted)} 个任务\n")

        for idx, task in enumerate(pending_sorted):
            task_id = task["id"]
            task_name = task["title"]
            task_type = task.get("type", "general")

            print(f"{'='*60}")
            print(f"[{idx+1}/{len(pending_sorted)}] 🔨 {task_id}: {task_name}")
            print(f"{'='*60}")

            self.manifest.start_task(task_id)
            self._save_manifest()

            dep_code = self._collect_dependency_code(task.get("dependencies", []))
            filtered_arch = self._filter_architecture_docs(task_type, arch)

            prompt = f"""## 任务信息

任务ID: {task_id}
任务名称: {task_name}
任务描述: {task.get('description', '')}
任务类型: {task_type}

## 技术架构要求

{filtered_arch}

## 依赖代码

{dep_code if dep_code else '无前置依赖'}

## 要求

请根据上述信息生成完整的代码文件。确保：
1. 遵循技术栈要求
2. 与依赖代码的接口、类型、命名完全一致
3. 遵循项目的目录结构规范
4. 代码完整可运行
"""

            codegen_agent = CodegenAgent(self.llm, str(self.working_dir), self.config)
            generated_files = codegen_agent.run_with_log(prompt, verbose=True)

            task_files = [TaskFile(**f) for f in generated_files]

            self.manifest.complete_task(task_id, task_files)
            self.generated_code_cache[task_id] = generated_files
            self._save_manifest()

            print(f"✅ 生成完成，共 {len(generated_files)} 个文件")
            for f in generated_files:
                print(f"   - {f['file_path']}")
            print()

        print("🔍 开始质量检查...")
        checker = QualityChecker(self.llm, str(self.working_dir), self.config.prompts_dir)

        tech_stack_desc = f"""Backend: {arch.get('backend', {}).get('framework', '')}
Frontend: {arch.get('frontend', {}).get('framework', '')}"""

        project_tree = "\n".join([
            str(p.relative_to(self.working_dir))
            for p in self.working_dir.rglob("*")
            if p.is_file() and "__pycache__" not in str(p)
        ])

        commands = checker.generate_check_commands(tech_stack_desc, project_tree)
        print("📋 检查命令:")
        for step, cmds in commands.items():
            if cmds:
                print(f"   {step}: {cmds}")

        result = checker.run_all()
        if not result.passed:
            print(f"❌ {result.step_name} 失败")
            print("\n".join(result.errors[:5]))

            print("\n🔧 开始自动修复...")
            fix_agent = FixAgent(self.llm, str(self.working_dir), self.config)
            fix_prompt = f"""## 质量检查失败

失败步骤: {result.step_name}

错误信息:
{chr(10).join(result.errors)}

请修复这些错误。可以先读取相关文件，然后覆盖修复。
"""
            fix_agent.run_with_log(fix_prompt, verbose=True)
            print("✅ 修复完成")
        else:
            print("✅ 所有质量检查通过")

        return {
            "session_id": self.manifest.session_id,
            "total_tasks": self.manifest.total_tasks,
            "completed_tasks": self.manifest.completed_tasks,
            "success": True,
        }
