from typing import Any, Dict, List

from langchain_core.tools import StructuredTool, tool

from .base_agent import BaseAgent

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


class PlanningAgent(BaseAgent):
    """任务规划 Agent

    理解 PRD + Architecture -> 输出结构化任务列表 + 依赖图
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

    def run_and_parse(self, prd_content: str, arch_content: str, verbose: bool = True) -> List[Dict[str, Any]]:
        """运行规划并返回解析后的任务列表

        Args:
            prd_content: PRD 文档内容
            arch_content: 架构文档内容
            verbose: 是否输出详细日志
        """
        template = self.prompt_loader.load("plan_tasks")
        prompt = template.render(prd_content=prd_content, arch_content=arch_content)

        callback = self.default_tool_callback if verbose else None
        self.run(prompt, tool_callback=callback)
        return self.get_task_graph()
