import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from prompts import PromptTemplate, get_prompt_loader

from .utils.shell import run_shell_command

logger = logging.getLogger(__name__)


def _ensure_list(value: Any, default: Optional[List[str]] = None) -> List[str]:
    """确保值是列表类型，用于容错处理。

    字符串转为单元素列表，None 或其他类型转为默认空列表。
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return default or []


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    failed_step: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    step_name: Optional[str] = None
    error_count: int = 0  # 错误总数（用于判断修复是否有效）


class QualityChecker:
    """动态质量检查器

    根据技术栈动态生成检查命令，不硬编码
    支持步骤化执行，从失败步骤恢复
    """

    STEP_ORDER = ["install", "lint", "type_check", "test"]
    STEP_NAMES = {
        "install": "依赖安装",
        "lint": "代码检查",
        "type_check": "类型检查",
        "test": "测试执行",
    }

    def __init__(self, llm: ChatOpenAI, working_dir: str, prompts_dir: Optional[str] = None):
        self.llm = llm
        self.working_dir = working_dir
        self.check_commands: Dict[str, List[str]] = {}

        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader(prompts_dir)

    def generate_check_commands(self, tech_stack: str, project_tree: str) -> Dict[str, List[str]]:
        """让 AI 根据技术栈动态生成检查命令

        Args:
            tech_stack: 技术栈描述
            project_tree: 项目目录结构

        Returns:
            {install: [...], lint: [...], type_check: [...], test: [...]}
        """
        template: PromptTemplate = self.prompt_loader.load("quality_checker")
        prompt = template.render(tech_stack=tech_stack, project_tree=project_tree)

        response = self.llm.invoke(prompt)
        content = response.content.strip()

        try:
            data = json.loads(content)
            self.check_commands = {
                "install": _ensure_list(data.get("install", [])),
                "lint": _ensure_list(data.get("lint", [])),
                "type_check": _ensure_list(data.get("type_check", [])),
                "test": _ensure_list(data.get("test", [])),
            }
        except json.JSONDecodeError as e:
            print(f"⚠️ 质量检查命令解析失败: {e}")
            print(f"   LLM 返回内容前200字符: {content[:200]}...")
            self.check_commands = {"install": [], "lint": [], "type_check": [], "test": []}

        return self.check_commands

    def _run_command(self, cmd: str) -> tuple[bool, str]:
        """执行单个 shell 命令（委托给通用工具函数）"""
        return run_shell_command(cmd, self.working_dir, timeout=300)

    def run_step(self, step_name: str) -> tuple[bool, List[str], int]:
        """执行单个检查步骤

        Returns:
            (是否成功, 错误列表, 真实错误数)
            真实错误数：统计错误输出中的非空行数（近似错误数量）
        """
        commands = self.check_commands.get(step_name, [])
        if not commands:
            return True, [], 0

        all_errors = []
        total_error_lines = 0
        for cmd in commands:
            success, output = self._run_command(cmd)
            if not success:
                error_msg = f"命令失败: {cmd}\n{output}"
                all_errors.append(error_msg)
                # 统计输出中的非空行数（近似真实错误数量）
                # 避免把 10 个 lint 错误只算成 1 个
                error_lines = [line for line in output.splitlines() if line.strip()]
                total_error_lines += len(error_lines)

        # 如果没有错误行但有错误（比如命令异常退出），至少算 1 个错误
        if all_errors and total_error_lines == 0:
            total_error_lines = len(all_errors)

        return len(all_errors) == 0, all_errors, total_error_lines

    def run_all(self, start_from: int = 0) -> CheckResult:
        """串行执行所有检查

        Args:
            start_from: 从第 N 步开始执行（跳过已成功的步骤）

        Returns:
            CheckResult 检查结果
        """
        for step_idx in range(start_from, len(self.STEP_ORDER)):
            step_name = self.STEP_ORDER[step_idx]
            if not self.check_commands.get(step_name):
                continue

            success, errors, error_count = self.run_step(step_name)
            if not success:
                return CheckResult(
                    passed=False,
                    failed_step=step_idx,
                    errors=errors,
                    step_name=step_name,
                    error_count=error_count,  # 用真实错误行数，不是命令数
                )

        return CheckResult(passed=True, error_count=0)

    def get_step_name(self, step_idx: int) -> str:
        """获取步骤名称"""
        if 0 <= step_idx < len(self.STEP_ORDER):
            return self.STEP_NAMES.get(self.STEP_ORDER[step_idx], "")
        return ""
