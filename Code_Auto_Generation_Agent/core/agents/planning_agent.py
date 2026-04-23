import json
import logging
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool, tool

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# === 模块级工具工厂：避免每次实例化都重新定义嵌套函数 ===


def _create_add_task(task_graph_validator: Dict[str, Any]) -> StructuredTool:
    """创建 add_task 工具"""
    @tool
    def add_task(task_id: str, title: str, description: str,
                 task_type: str = "general", dependencies: List[str] = []) -> str:
        """添加一个任务到任务图

        Args:
            task_id: 任务唯一标识，如 T001, T002
            title: 任务简短标题
            description: 任务详细描述，包含验收标准
            task_type: 任务类型：backend, frontend, database, shared, infrastructure
            dependencies: 依赖的任务 ID 列表
        """
        # 立即检查重复 ID，提前发现问题
        existing_ids = {t["id"] for t in task_graph_validator["tasks"]}
        if task_id in existing_ids:
            return f"⚠️ 错误: 任务 ID 已存在: {task_id}"

        task_graph_validator["tasks"].append({
            "id": task_id,
            "title": title,
            "description": description,
            "type": task_type,
            "dependencies": dependencies or [],
        })
        return f"✓ 已添加任务: {task_id} - {title}"
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


_MODULE_PREFIX_MAP = {
    "backend": "B",
    "frontend": "F",
    "database": "D",
    "shared": "S",
    "infrastructure": "I",
}


class PlanningAgent(BaseAgent):
    """任务规划 Agent（分阶段版本）

    阶段1：解析架构 -> 提取模块列表
    阶段2：逐个模块规划任务（多次 LLM 调用，每次只处理一个模块）
    阶段3：跨模块依赖整理 -> 统一编号
    """

    def _get_prompt_template_name(self) -> str:
        return "planning_agent"

    def _init_tools(self) -> List:
        """定义规划工具（使用模块级工厂函数创建）"""
        task_graph_validator = {"tasks": []}
        self._task_graph_ref = task_graph_validator

        return [
            _create_add_task(task_graph_validator),
            _create_validate_task_graph(task_graph_validator),
            _create_finish(task_graph_validator),
        ]

    def get_task_graph(self) -> List[Dict[str, Any]]:
        """获取最终的任务图"""
        return self._task_graph_ref["tasks"]

    def _clear_task_graph(self) -> None:
        """清空任务图（用于多轮规划）"""
        self._task_graph_ref["tasks"] = []
        self._task_graph_ref["validated"] = False

    def _extract_modules(self, prd_desc: str, arch_desc: str) -> List[Dict[str, str]]:
        """阶段1：从架构文档提取模块列表

        Returns:
            [{"name": "backend", "description": "...", "prefix": "B"}, ...]
        """
        print("  📋 阶段1: 提取模块列表...")
        template = self.prompt_loader.load("plan_stage1_extract_modules")
        prompt = template.render(prd_content=prd_desc, arch_content=arch_desc)

        # 直接调用 LLM（不需要工具调用，只需要 JSON 输出）
        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # 解析 JSON
        try:
            # 提取 ```json ... ``` 包裹的部分
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()
            data = json.loads(json_str)
            modules = data.get("modules", [])

            # 添加 prefix
            for m in modules:
                m["prefix"] = _MODULE_PREFIX_MAP.get(m["name"], m["name"][0].upper())

            logger.info(f"提取到 {len(modules)} 个模块: {[m['name'] for m in modules]}")
            return modules

        except json.JSONDecodeError as e:
            logger.warning(f"解析模块列表失败，直接从架构文档解析: {e}")
            # 兜底：直接从架构 JSON 中解析模块（Coordinator 已保证至少有 backend/frontend）
            arch = json.loads(arch_desc)
            modules = []
            for key in ["backend", "frontend", "database", "shared", "infrastructure"]:
                if key in arch:
                    modules.append({
                        "name": key,
                        "description": f"{key} 模块",
                        "prefix": _MODULE_PREFIX_MAP.get(key, key[0].upper())
                    })
            return modules

    def _plan_module_tasks(self, module: Dict[str, str], prd_desc: str,
                           arch_desc: str, verbose: bool) -> List[Dict[str, Any]]:
        """阶段2：规划单个模块的任务"""
        print(f"  🔨 阶段2: 规划 {module['name']} 模块...")
        self._clear_task_graph()

        template = self.prompt_loader.load("plan_stage2_module_tasks")
        prompt = template.render(
            prd_content=prd_desc,
            arch_content=arch_desc,
            module_name=module["name"],
            module_desc=module["description"],
            module_prefix=module["prefix"],
        )

        callback = self.default_tool_callback if verbose else None
        self.run(prompt, tool_callback=callback)

        tasks = self.get_task_graph()
        logger.info(f"模块 {module['name']} 生成 {len(tasks)} 个任务")
        return tasks

    def _resolve_cross_module_deps(self, all_tasks: List[Dict[str, Any]],
                                    prd_desc: str, arch_desc: str) -> List[Dict[str, Any]]:
        """阶段3：跨模块依赖整理 + 统一编号"""
        print("  🔗 阶段3: 整理跨模块依赖...")

        # 按类型排序：database -> backend -> frontend -> ...
        type_order = {"database": 0, "shared": 1, "backend": 2, "frontend": 3, "infrastructure": 4}
        all_tasks.sort(key=lambda t: type_order.get(t.get("type", ""), 99))

        # 调用 LLM 做智能的跨模块依赖整理
        template = self.prompt_loader.load("plan_stage3_resolve_deps")
        prompt = template.render(
            all_tasks_json=json.dumps(all_tasks, ensure_ascii=False, indent=2),
            prd_content=prd_desc,
            arch_content=arch_desc,
        )

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        try:
            # 提取 ```json ... ``` 包裹的部分
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()
            data = json.loads(json_str)
            tasks = data.get("tasks", [])

            if tasks:
                logger.info(f"跨模块依赖整理完成，共 {len(tasks)} 个任务")
                return tasks
        except json.JSONDecodeError as e:
            logger.warning(f"解析依赖整理结果失败: {e}")

        # 兜底：简单重新编号，依赖保持原编号
        print("    ⚠️ 使用简单编号模式")
        id_map = {}
        for i, task in enumerate(all_tasks, 1):
            old_id = task["id"]
            new_id = f"T{i:03d}"
            id_map[old_id] = new_id

        result = []
        for task in all_tasks:
            result.append({
                "id": id_map[task["id"]],
                "title": task["title"],
                "description": task.get("description", ""),
                "type": task.get("type", "general"),
                "dependencies": [id_map.get(d, d) for d in task.get("dependencies", [])],
            })

        return result

    def run_with_log(self, prd_desc: str, architecture_desc: str,
                     verbose: bool = True) -> List[Dict[str, Any]]:
        """运行任务规划并输出实时日志（分阶段版本）

        Args:
            prd_desc: PRD 文档内容（JSON 格式）
            architecture_desc: 架构文档内容（JSON 格式）
            verbose: 是否输出详细日志

        Returns:
            解析后的任务列表
        """
        print("\n🎯 开始分阶段任务规划...")

        # 阶段1：提取模块列表
        modules = self._extract_modules(prd_desc, architecture_desc)
        print(f"    提取到 {len(modules)} 个模块: {', '.join(m['name'] for m in modules)}")

        # 阶段2：逐个模块规划任务
        all_tasks = []
        for module in modules:
            module_tasks = self._plan_module_tasks(module, prd_desc, architecture_desc, verbose)
            all_tasks.extend(module_tasks)
            print(f"    {module['name']}: {len(module_tasks)} 个任务")

        print(f"    所有模块共 {len(all_tasks)} 个任务")

        # 阶段3：跨模块依赖整理
        final_tasks = self._resolve_cross_module_deps(all_tasks, prd_desc, architecture_desc)

        print(f"✅ 任务规划完成，共 {len(final_tasks)} 个任务\n")
        return final_tasks

    def run_and_parse(self, prd_content: str, arch_content: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """运行规划并返回解析后的任务列表（兼容旧接口）"""
        return self.run_with_log(prd_content, arch_content, verbose)
