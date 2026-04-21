import json
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

from langchain_openai import ChatOpenAI

from prompts import PromptTemplate, get_prompt_loader


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    failed_step: Optional[int] = None
    errors: List[str] = None
    step_name: Optional[str] = None


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

    def __init__(self, llm: ChatOpenAI, working_dir: str, prompts_dir: str = None):
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
                "install": data.get("install", []),
                "lint": data.get("lint", []),
                "type_check": data.get("type_check", []),
                "test": data.get("test", []),
            }
        except json.JSONDecodeError:
            self.check_commands = {"install": [], "lint": [], "type_check": [], "test": []}

        return self.check_commands

    def _run_command(self, cmd: str) -> tuple[bool, str]:
        """执行单个 shell 命令"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "命令执行超时（超过 5 分钟）"
        except Exception as e:
            return False, str(e)

    def run_step(self, step_name: str) -> tuple[bool, List[str]]:
        """执行单个检查步骤"""
        commands = self.check_commands.get(step_name, [])
        if not commands:
            return True, []

        all_errors = []
        for cmd in commands:
            success, output = self._run_command(cmd)
            if not success:
                all_errors.append(f"命令失败: {cmd}\n{output}")

        return len(all_errors) == 0, all_errors

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

            success, errors = self.run_step(step_name)
            if not success:
                return CheckResult(
                    passed=False,
                    failed_step=step_idx,
                    errors=errors,
                    step_name=step_name,
                )

        return CheckResult(passed=True)

    def get_step_name(self, step_idx: int) -> str:
        """获取步骤名称"""
        if 0 <= step_idx < len(self.STEP_ORDER):
            return self.STEP_NAMES.get(self.STEP_ORDER[step_idx], "")
        return ""
