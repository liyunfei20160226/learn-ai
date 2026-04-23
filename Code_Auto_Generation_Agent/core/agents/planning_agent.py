import json
import logging
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool, tool

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# === 模块级工具工厂：避免每次实例化都重新定义嵌套函数 ===


def _normalize_dep_id(dep: str) -> str:
    """标准化依赖 ID：处理 LLM 可能生成的各种格式

    LLM 生成依赖 ID 的格式不一致，需要统一处理：
    - "06", "6" → "T006"
    - "B-MOD-001_06" → "T006" (提取序号部分)
    - "T006" → "T006" (已经是正确格式)
    """
    import re

    # 纯数字或带零前缀的数字
    if dep.isdigit():
        return f"T{int(dep):03d}"

    # 下划线结尾后跟数字：如 B-MOD-001_06 → 提取 06
    match = re.search(r'_(\d+)$', dep)
    if match:
        return f"T{int(match.group(1)):03d}"

    return dep


def _create_add_task(task_graph_validator: Dict[str, Any]) -> StructuredTool:
    """创建 add_task 工具（内置 ID 实时修正，彻底解决跨模块 ID 冲突）

    module_id 从 task_graph_validator["_module_id"] 动态获取，这样可以在
    不同模块规划时直接修改这个字段，不需要重新创建工具。

    Args:
        task_graph_validator: 任务图验证器字典，包含 _module_id 字段
    """
    @tool
    def add_task(task_id: str, title: str, description: str,
                 task_type: str = "general", dependencies: List[str] = []) -> str:
        """添加一个任务到任务图

        注意：LLM 传入的 task_id 会被自动转换为 {module_id}_{序号} 格式，
        以确保跨模块规划时不会出现 ID 冲突。dependencies 也会被自动转换。

        Args:
            task_id: LLM 传入的任务 ID（会被自动转换）
            title: 任务简短标题
            description: 任务详细描述，包含验收标准
            task_type: 任务类型：backend, frontend, database, shared, infrastructure
            dependencies: 依赖的任务 ID 列表（会被自动转换）
        """
        # 初始化 ID 映射表（LLM ID → 真实 ID）
        if "id_mapping" not in task_graph_validator:
            task_graph_validator["id_mapping"] = {}

        # 从共享对象动态获取当前 module_id（关键：支持跨模块规划时切换）
        module_id = task_graph_validator.get("_module_id", "MODULE")

        # 按添加顺序生成真实 ID，格式：{module_id}_{序号:02d}
        next_idx = len(task_graph_validator["tasks"]) + 1
        real_id = f"{module_id}_{next_idx:02d}"  # e.g., B-MOD-001_01

        # 记录 LLM ID → 真实 ID 的映射（支持多种格式查找）
        task_graph_validator["id_mapping"][task_id] = real_id
        # 同时存入标准化后的 ID，方便依赖查找（LLM 格式不统一）
        normalized_llm_id = _normalize_dep_id(task_id)
        if normalized_llm_id != task_id:
            task_graph_validator["id_mapping"][normalized_llm_id] = real_id

        # 实时转换 dependencies 中的 ID（支持多种格式匹配）
        id_mapping = task_graph_validator["id_mapping"]
        real_dependencies = []
        for dep in (dependencies or []):
            # 先尝试原始 ID 查找，再尝试标准化 ID 查找
            if dep in id_mapping:
                real_dependencies.append(id_mapping[dep])
            else:
                normalized_dep = _normalize_dep_id(dep)
                if normalized_dep in id_mapping:
                    real_dependencies.append(id_mapping[normalized_dep])
                else:
                    real_dependencies.append(dep)  # 找不到映射就保留原样

        # 用真实 ID 添加任务（永远不会有 ID 冲突，因为按顺序生成）
        task_graph_validator["tasks"].append({
            "id": real_id,
            "title": title,
            "description": description,
            "type": task_type,
            "dependencies": real_dependencies,
        })

        # 返回时显示真实 ID，让用户看到正确格式
        return f"✓ 已添加任务: {real_id} - {title}"
    return add_task


def _create_validate_task_graph(task_graph_validator: Dict[str, Any]) -> StructuredTool:
    """创建 validate_task_graph 工具"""
    @tool
    def validate_task_graph() -> str:
        """验证当前任务图的有效性

        检查：
        1. 任务 ID 是否唯一
        2. 依赖的任务是否存在
        3. 是否有循环依赖（Kahn 算法检测）
        """
        tasks = task_graph_validator["tasks"]
        errors = []

        # 检查 1: 任务 ID 唯一性
        seen_ids = set()
        for task in tasks:
            if task["id"] in seen_ids:
                errors.append(f"任务 ID 重复: {task['id']}")
            seen_ids.add(task["id"])

        # 检查 2: 依赖的任务是否存在
        task_ids = seen_ids
        for task in tasks:
            for dep in task["dependencies"]:
                if dep not in task_ids:
                    errors.append(f"任务 {task['id']} 依赖不存在的任务 {dep}")

        # 检查 3: 是否有循环依赖（Kahn 算法）
        if not errors and tasks:
            in_degree = {t["id"]: len(t.get("dependencies", [])) for t in tasks}
            adj_list = {t["id"]: [] for t in tasks}

            for task in tasks:
                for dep in task.get("dependencies", []):
                    adj_list[dep].append(task["id"])

            queue = [tid for tid, deg in in_degree.items() if deg == 0]
            processed = 0

            while queue:
                task_id = queue.pop(0)
                processed += 1
                for next_id in adj_list[task_id]:
                    in_degree[next_id] -= 1
                    if in_degree[next_id] == 0:
                        queue.append(next_id)

            if processed != len(tasks):
                # 收集所有仍有入度的任务（即循环依赖中的任务）
                unresolved = [t["id"] for t in tasks if in_degree[t["id"]] > 0]
                errors.append(f"任务图存在循环依赖，无法解析以下任务: {sorted(unresolved)}")

        if not errors:
            errors.append("✓ 任务图验证通过")
            task_graph_validator["validated"] = True

        return "\n".join(errors)
    return validate_task_graph


def _create_finish(task_graph_validator: Dict[str, Any]) -> StructuredTool:
    """创建 finish 工具"""
    @tool
    def finish(summary: str) -> str:
        """标记任务规划完成

        Args:
            summary: 任务规划总结
        """
        if not task_graph_validator.get("validated", False):
            return "⚠️ 错误：在完成之前必须先调用 validate_task_graph 验证任务图！"
        return f"✅ 任务规划完成\n{summary}"
    return finish


class PlanningAgent(BaseAgent):
    """任务规划 Agent（基于架构文档直接拆分）

    4 阶段细粒度拆分，彻底解决超时问题：
    1. 从架构文档提取顶层模块（backend/frontend/shared...）
    2. 从架构文档提取每个顶层模块下的架构模块（JSON 直接解析，不需要 LLM）
    3. 逐个架构模块规划任务（每个模块只包含少量 user story，不超时）
    4. 跨模块依赖整理 + 统一编号
    """

    def _get_prompt_template_name(self) -> str:
        return "planning_agent"

    def _init_tools(self) -> List:
        """定义规划工具（通过共享状态动态绑定，module_id 运行时注入）

        关键设计：工具闭包绑定到同一个 `self._task_graph_ref` 可变字典，
        后续只需要修改 `self._task_graph_ref["_module_id"]` 即可切换当前模块，
        不需要重新创建工具或重新编译 graph。
        """
        task_graph_validator: Dict[str, Any] = {"tasks": [], "id_mapping": {}}
        self._task_graph_ref = task_graph_validator

        # 注意：_create_add_task 现在只需要一个参数
        # module_id 通过 task_graph_validator["_module_id"] 动态获取
        return [
            _create_add_task(task_graph_validator),
            _create_validate_task_graph(task_graph_validator),
            _create_finish(task_graph_validator),
        ]

    def get_task_graph(self) -> List[Dict[str, Any]]:
        """获取最终的任务图"""
        return self._task_graph_ref["tasks"]

    def _clear_task_graph(self) -> None:
        """清空任务图（完整清理所有状态）"""
        self._task_graph_ref.clear()
        self._task_graph_ref["tasks"] = []
        self._task_graph_ref["id_mapping"] = {}
        self._task_graph_ref["validated"] = False

    def _extract_stories_by_ids(self, prd: Dict[str, Any], story_ids: List[str]) -> List[Dict[str, Any]]:
        """根据 ID 列表从 PRD 中提取对应的 user story"""
        id_set = set(story_ids)
        return [us for us in prd.get("userStories", []) if us["id"] in id_set]

    def _extract_arch_modules(self, architecture_desc: str) -> List[Dict[str, Any]]:
        """阶段 1+2：从架构文档 JSON 中直接提取所有模块

        返回扁平化的模块列表（所有技术栈混合，通过 type 字段区分）
        """
        arch = json.loads(architecture_desc)
        all_modules = []

        # 后端模块
        for module in arch.get("backend", {}).get("modules", []):
            module["type"] = "backend"
            module["module_id"] = module["id"]  # 保留原 ID 如 B-MOD-001
            all_modules.append(module)

        # 前端模块
        for module in arch.get("frontend", {}).get("modules", []):
            module["type"] = "frontend"
            module["module_id"] = module["id"]
            all_modules.append(module)

        # shared/infrastructure 等其他模块
        # 可以在这里扩展

        logger.info(f"从架构文档提取到 {len(all_modules)} 个模块")
        return all_modules

    def _plan_single_module_tasks(self, module: Dict[str, Any], stories: List[Dict[str, Any]],
                                  verbose: bool) -> List[Dict[str, Any]]:
        """阶段 3：规划单个架构模块的任务"""
        module_id = module["module_id"]

        # 关键：原地修改共享字典，而不是重新赋值！
        # 因为 graph 已经编译，工具闭包绑定了原始的 self._task_graph_ref 引用
        # 原地清空 + 设置当前 module_id，这样工具闭包能读到正确的值
        self._task_graph_ref.clear()
        self._task_graph_ref["tasks"] = []
        self._task_graph_ref["id_mapping"] = {}
        self._task_graph_ref["validated"] = False
        self._task_graph_ref["_module_id"] = module_id  # 动态注入当前模块 ID

        template = self.prompt_loader.load("plan_module_tasks")
        prompt = template.render(
            module_id=module_id,
            module_name=module["name"],
            module_description=module["description"],
            module_directory=module["directory"],
            files_json=json.dumps(module.get("files", []), ensure_ascii=False, indent=2),
            stories_json=json.dumps(stories, ensure_ascii=False, indent=2),
        )

        callback = self.default_tool_callback if verbose else None
        self.run(prompt, tool_callback=callback)

        tasks = self.get_task_graph()

        # 加上模块来源标记和类型标记
        for task in tasks:
            task["_source_module_id"] = module_id
            task["type"] = module["type"]  # 确保类型正确

        logger.info(f"模块 {module_id} {module['name']} 生成 {len(tasks)} 个任务")
        return tasks

    def _resolve_cross_module_deps(self, all_tasks: List[Dict[str, Any]],
                                    architecture_desc: str) -> List[Dict[str, Any]]:
        """阶段 4：跨模块依赖整理 + 统一编号

        从架构文档提取模块间依赖关系，不需要 LLM
        """
        arch = json.loads(architecture_desc)

        # 构建模块 ID -> 任务 ID 列表的映射
        module_tasks_map: Dict[str, List[str]] = {}
        for task in all_tasks:
            mid = task.get("_source_module_id")
            if mid:
                module_tasks_map.setdefault(mid, []).append(task["id"])

        # 统一编号 T001, T002, ...
        id_mapping = {}
        result = []
        for i, task in enumerate(all_tasks, 1):
            new_id = f"T{i:03d}"
            id_mapping[task["id"]] = new_id
            result.append({
                "id": new_id,
                "title": task["title"],
                "description": task.get("description", ""),
                "type": task.get("type", "general"),
                "dependencies": [],  # 稍后处理
            })

        # 转换原有的模块内依赖
        for old_task, new_task in zip(all_tasks, result):
            new_deps = [id_mapping[dep] for dep in old_task.get("dependencies", []) if dep in id_mapping]
            new_task["dependencies"] = new_deps

        # 从架构文档提取跨模块依赖，添加到第一个任务上
        module_deps_map: Dict[str, List[str]] = {}
        for module in arch.get("backend", {}).get("modules", []):
            module_deps_map[module["id"]] = module.get("dependencies", [])
        for module in arch.get("frontend", {}).get("modules", []):
            module_deps_map[module["id"]] = module.get("dependencies", [])

        # 应用跨模块依赖：如果模块 A 依赖模块 B，那么 A 的第一个任务依赖 B 的最后一个任务
        module_last_task: Dict[str, str] = {}
        for task in reversed(result):
            mid = all_tasks[result.index(task)].get("_source_module_id")
            if mid and mid not in module_last_task:
                module_last_task[mid] = task["id"]

        for i, task in enumerate(result):
            mid = all_tasks[i].get("_source_module_id")
            if mid and mid in module_deps_map:
                for dep_module_id in module_deps_map[mid]:
                    if dep_module_id in module_last_task and module_last_task[dep_module_id] != task["id"]:
                        if module_last_task[dep_module_id] not in task["dependencies"]:
                            task["dependencies"].append(module_last_task[dep_module_id])

        logger.info(f"跨模块依赖整理完成，共 {len(result)} 个任务")
        return result

    def run_with_log(self, prd_desc: str, architecture_desc: str,
                     verbose: bool = True) -> List[Dict[str, Any]]:
        """运行任务规划并输出实时日志

        Args:
            prd_desc: PRD 文档内容（JSON 格式）
            architecture_desc: 架构文档内容（JSON 格式）
            verbose: 是否输出详细日志

        Returns:
            解析后的任务列表
        """
        prd = json.loads(prd_desc)

        print("\n🎯 开始任务规划（基于架构文档拆分）...", flush=True)

        # 阶段 1+2：从架构文档直接提取所有模块（不需要 LLM）
        modules = self._extract_arch_modules(architecture_desc)
        print(f"  ✓ 从架构文档提取到 {len(modules)} 个模块:", flush=True)
        for m in modules:
            print(f"    - {m['module_id']}: {m['name']} ({len(m.get('userStoryIds', []))} 个需求)", flush=True)

        # 阶段 3：逐个模块规划任务（每个模块 1 次 LLM 调用，不超时）
        all_tasks = []
        for i, module in enumerate(modules, 1):
            stories = self._extract_stories_by_ids(prd, module.get("userStoryIds", []))
            print(f"\n  🔨 [{i}/{len(modules)}] 规划 {module['module_id']}: {module['name']} ({len(stories)} 个需求)", flush=True)
            module_tasks = self._plan_single_module_tasks(module, stories, verbose)
            all_tasks.extend(module_tasks)
            print(f"    ✓ 生成 {len(module_tasks)} 个任务", flush=True)

        print(f"\n  ✓ 所有模块共生成 {len(all_tasks)} 个任务", flush=True)

        # 阶段 4：跨模块依赖整理 + 统一编号（不需要 LLM，直接解析架构文档）
        print("  🔗 整理跨模块依赖关系...", flush=True)
        final_tasks = self._resolve_cross_module_deps(all_tasks, architecture_desc)

        print(f"\n✅ 任务规划完成，共 {len(final_tasks)} 个任务\n", flush=True)
        return final_tasks

    def run_and_parse(self, prd_content: str, arch_content: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """运行规划并返回解析后的任务列表（兼容旧接口）"""
        return self.run_with_log(prd_content, arch_content, verbose)
