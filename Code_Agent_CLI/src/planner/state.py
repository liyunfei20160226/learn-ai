"""
Planner 状态管理

定义计划模式的状态机和数据结构。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class PlanMode(Enum):
    """计划模式的状态"""
    IDLE = "idle"                  # 不在计划模式，正常执行
    WAITING_FOR_CONFIRM = "waiting_confirm"   # 已生成计划，等待用户确认
    EXECUTING = "executing"        # 用户已确认，正在按计划执行
    ADJUSTING = "adjusting"        # 用户提出修改，正在调整计划


@dataclass
class PlanStep:
    """计划中的一个步骤"""
    step_id: int
    description: str              # 步骤描述
    expected_outcome: str = ""    # 预期结果
    # 执行状态
    status: Literal["pending", "in_progress", "done", "failed", "skipped"] = "pending"
    result_summary: Optional[str] = None  # 执行结果摘要

    def to_dict(self) -> Dict[str, Any]:
        """序列化到字典"""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "expected_outcome": self.expected_outcome,
            "status": self.status,
            "result_summary": self.result_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        """从字典反序列化"""
        return cls(
            step_id=data["step_id"],
            description=data["description"],
            expected_outcome=data.get("expected_outcome", ""),
            status=data.get("status", "pending"),
            result_summary=data.get("result_summary"),
        )


@dataclass
class Plan:
    """完整的执行计划"""
    plan_id: str
    goal: str                     # 最终目标
    steps: List[PlanStep]         # 步骤列表
    notes: List[str]              # 注意事项

    # 执行状态
    current_step_index: int = 0
    mode: PlanMode = PlanMode.WAITING_FOR_CONFIRM

    # 用户修改历史
    user_feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """序列化到字典（用于会话持久化）"""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "notes": self.notes,
            "current_step_index": self.current_step_index,
            "mode": self.mode.value,
            "user_feedback": self.user_feedback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        """从字典反序列化"""
        return cls(
            plan_id=data["plan_id"],
            goal=data["goal"],
            steps=[PlanStep.from_dict(s) for s in data["steps"]],
            notes=data.get("notes", []),
            current_step_index=data.get("current_step_index", 0),
            mode=PlanMode(data.get("mode", "waiting_confirm")),
            user_feedback=data.get("user_feedback", []),
        )
