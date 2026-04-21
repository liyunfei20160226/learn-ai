from typing import Any, Dict, List

from langchain_core.tools import tool

from .base_agent import BaseAgent


class PlanningAgent(BaseAgent):
    """任务规划 Agent

    理解 PRD + Architecture -> 输出结构化任务列表 + 依赖图
    """

    def _get_prompt_template_name(self) -> str:
        return "planning_agent"

    def _init_tools(self) -> List:
        """定义规划工具"""
        task_graph_validator = {"tasks": []}

        @tool
        def add_task(task_id: str, title: str, description: str,
                     task_type: str = "general", dependencies: List[str] = None) -> str:
            """添加一个任务到任务图

            Args:
                task_id: 任务唯一标识，如 T001, T002
                title: 任务简短标题
                description: 任务详细描述，包含验收标准
                task_type: 任务类型：backend, frontend, shared, infrastructure
                dependencies: 依赖的任务 ID 列表
            """
            task_graph_validator["tasks"].append({
                "id": task_id,
                "title": title,
                "description": description,
                "type": task_type,
                "dependencies": dependencies or [],
            })
            return f"✓ 已添加任务: {task_id} - {title}"

        @tool
        def validate_task_graph() -> str:
            """验证当前任务图的有效性

            检查：
            1. 依赖的任务是否存在
            2. 是否有循环依赖
            3. 任务 ID 是否唯一
            """
            tasks = task_graph_validator["tasks"]
            task_ids = {t["id"] for t in tasks}
            errors = []

            for task in tasks:
                for dep in task["dependencies"]:
                    if dep not in task_ids:
                        errors.append(f"任务 {task['id']} 依赖不存在的任务 {dep}")

            if not errors:
                errors.append("✓ 任务图验证通过")
                task_graph_validator["validated"] = True

            return "\n".join(errors)

        @tool
        def finish(summary: str) -> str:
            """标记任务规划完成

            Args:
                summary: 任务规划总结
            """
            if not task_graph_validator.get("validated", False):
                return "⚠️ 错误：在完成之前必须先调用 validate_task_graph 验证任务图！"
            return f"✅ 任务规划完成\n{summary}"

        self._task_graph_ref = task_graph_validator
        return [add_task, validate_task_graph, finish]

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
        prompt = f"""## PRD 需求文档

{prd_content}

## Architecture 架构文档

{arch_content}

请根据上述文档，规划完整的代码生成任务列表。
"""

        def tool_callback(node_name: str, tool_name: str, result: str):
            if verbose:
                if tool_name == "add_task":
                    print(f"  🛠️  {result}")
                elif tool_name == "validate_task_graph":
                    print("  🔍  验证任务图...")
                    for line in result.split("\n"):
                        print(f"     {line}")
                elif tool_name == "finish":
                    print(f"  🏁  {result}")

        self.run_stream(prompt, tool_callback=tool_callback)
        return self.get_task_graph()
