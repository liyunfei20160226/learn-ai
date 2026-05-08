"""
PlanTool - 计划生成工具

让 LLM 可以为复杂任务生成执行计划。
生成计划后，Agent 会暂停执行，等待用户确认。

设计原则：
- 不硬编码前置判断，LLM 自己决定什么时候需要计划
- 自主迭代：LLM 自己评估计划质量，不满意就继续优化
- 用户永远有最终控制权
"""
import json
import uuid
from typing import Any, Dict

from .base import BaseTool, PlanCreatedPause
from planner.state import Plan, PlanStep, PlanMode


class PlanTool(BaseTool):
    """
    计划工具 - 让 LLM 可以生成执行计划

    LLM 觉得任务复杂时，应该主动调用这个工具来生成计划。
    生成计划后，Agent 会暂停执行，等待用户确认或修改。
    """

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return """
为复杂任务生成执行计划。

当你觉得任务需要多步操作、或可能走弯路时，调用这个工具。
生成计划后，用户有机会确认或修改，然后才开始执行。

注意：
- 不要每个小问题都生成计划，只有真正复杂的才用
- 计划应该有 3-7 个步骤
- 每个步骤要有明确的目标
- 生成后必须做自评估（self_check）
""".strip()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "这个任务最终要达成的目标",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "步骤描述",
                            },
                            "expected_outcome": {
                                "type": "string",
                                "description": "预期结果",
                            },
                        },
                        "required": ["description"],
                    },
                },
                "notes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要用户注意的事项或风险点",
                },
                "self_check": {
                    "type": "object",
                    "description": "计划自评估（生成计划后必须做！）",
                    "properties": {
                        "coverage": {
                            "type": "string",
                            "description": "是否完整覆盖了用户所有需求？",
                        },
                        "order": {
                            "type": "string",
                            "description": "步骤顺序是否合理？",
                        },
                        "missing": {
                            "type": "string",
                            "description": "有没有遗漏的关键环节？比如备份、测试、回滚方案？",
                        },
                        "risks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "可能的风险点",
                        },
                        "needs_further_iteration": {
                            "type": "boolean",
                            "description": "是否需要继续优化这个计划？（不满意就返回 true，自己修正）",
                        },
                        "reason": {
                            "type": "string",
                            "description": "说明为什么需要/不需要继续迭代？",
                        },
                    },
                    "required": [
                        "coverage",
                        "order",
                        "missing",
                        "risks",
                        "needs_further_iteration",
                        "reason",
                    ],
                },
            },
            "required": ["goal", "steps", "self_check"],
        }

    async def run(self, arguments: Dict[str, Any]) -> str:
        """
        执行计划生成

        核心逻辑：
        1. 接收 LLM 生成的初始计划
        2. 如果 LLM 自评估说需要改进，自主迭代优化（最多 5 轮）
        3. 迭代完成后，创建 Plan 对象并挂载到 Agent
        4. 抛出 PlanCreatedPause 暂停执行，等待用户确认
        """
        plan_data = arguments
        iterations = 1
        improvement_notes = []

        # ========== 自主迭代优化 ==========
        while (
            plan_data["self_check"]["needs_further_iteration"]
            and iterations < 5
        ):
            iterations += 1
            reason = plan_data["self_check"]["reason"]
            improvement_notes.append(f"第 {iterations-1} 轮改进: {reason}")

            # 让 LLM 根据自己的评估修正计划
            revise_prompt = f"""
你上一轮的自评估认为还需要改进：
{reason}

请修正这个计划，保持完全相同的 JSON 格式。
做完后再次评估，如果还不满意就继续返回 needs_further_iteration: true，
满意了就返回 false。

重要：只输出 JSON，不要其他文字。
"""

            try:
                from main import get_agent

                agent = get_agent()
                revised_text = await agent.llm.chat(revise_prompt)

                # 解析 JSON
                revised_text = revised_text.strip()
                if revised_text.startswith("```"):
                    revised_text = revised_text.split("\n", 1)[1].rsplit("\n", 1)[0]
                if revised_text.startswith("```json"):
                    revised_text = revised_text.split("\n", 1)[1].rsplit("\n", 1)[0]

                plan_data = json.loads(revised_text.strip())

            except Exception as e:
                # 迭代失败，停止迭代，用当前计划
                improvement_notes.append(f"迭代失败，使用当前计划: {e}")
                break

        # ========== 迭代完成，创建 Plan 对象 ==========
        plan = Plan(
            plan_id=str(uuid.uuid4())[:8],
            goal=plan_data["goal"],
            steps=[
                PlanStep(
                    step_id=i + 1,
                    description=step["description"],
                    expected_outcome=step.get("expected_outcome", ""),
                )
                for i, step in enumerate(plan_data["steps"])
            ],
            notes=plan_data.get("notes", []),
            mode=PlanMode.WAITING_FOR_CONFIRM,
        )

        # 挂载到 Agent
        try:
            from main import get_agent

            agent = get_agent()
            agent.current_plan = plan
        except Exception:
            # 如果取不到全局 agent，降级方案
            pass

        # ========== 格式化显示给用户 ==========
        display = self._format_plan_for_display(
            plan, plan_data, iterations, improvement_notes
        )

        # 抛出异常暂停执行
        raise PlanCreatedPause(display)

    def _format_plan_for_display(
        self,
        plan: Plan,
        plan_data: dict,
        iterations: int,
        improvement_notes: list,
    ) -> str:
        """格式化计划用于控制台显示"""
        lines = ["📋 我建议按以下计划执行：", ""]

        # 目标
        lines.append(f"🎯 目标：{plan.goal}")
        lines.append("")

        # 步骤
        for step in plan.steps:
            status_icon = "⏳"
            lines.append(f"  {step.step_id}. {status_icon} {step.description}")
            if step.expected_outcome:
                lines.append(f"       预期：{step.expected_outcome}")
            lines.append("")

        # 注意事项
        if plan.notes:
            lines.append("⚠️  注意事项：")
            for note in plan.notes:
                lines.append(f"  • {note}")
            lines.append("")

        # 自主优化说明
        if iterations > 1:
            lines.append(f"✨ 经过 {iterations} 轮自主优化：")
            for note in improvement_notes:
                lines.append(f"  • {note}")
            lines.append("")
        else:
            lines.append("✨ 已通过自评估")
            lines.append("")

        # 自评估结果
        self_check = plan_data["self_check"]
        lines.append(f"  • 需求覆盖：{self_check['coverage']}")
        lines.append(f"  • 步骤顺序：{self_check['order']}")
        lines.append(f"  • 遗漏检查：{self_check['missing']}")
        if self_check["risks"]:
            lines.append("  • 风险点：")
            for risk in self_check["risks"]:
                lines.append(f"    - {risk}")
        lines.append("")

        # 用户操作提示
        lines.append("❓ 这个计划可以吗？你可以：")
        lines.append("   • 直接回车确认")
        lines.append("   • 告诉我要修改的地方（比如\"跳过第5步测试\"）")
        lines.append("   • 增加你想要的步骤")
        lines.append("   • /abort 放弃计划")

        return "\n".join(lines)
