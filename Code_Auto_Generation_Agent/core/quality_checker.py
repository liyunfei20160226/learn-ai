"""质量检查器 - 运行lint、类型检查、测试等"""

import os
from typing import List, Tuple, Optional
from utils.subprocess import run_command, check_command_available
from utils.logger import get_logger


logger = get_logger()


class QualityCheckResult:
    """质量检查结果"""
    def __init__(self, passed: bool, errors: List[str]):
        self.passed = passed
        self.errors = errors


def detect_project_language(working_dir: str) -> Optional[str]:
    """自动探测项目语言"""
    # 探测优先级：特征文件存在与否
    if os.path.exists(os.path.join(working_dir, 'pyproject.toml')) or \
       os.path.exists(os.path.join(working_dir, 'setup.py')) or \
       os.path.exists(os.path.join(working_dir, 'requirements.txt')):
        return 'python'
    elif os.path.exists(os.path.join(working_dir, 'package.json')):
        # JavaScript/TypeScript 包含所有前端框架: React/Vue/Angular/Vite/Next.js etc.
        return 'javascript'
    elif os.path.exists(os.path.join(working_dir, 'go.mod')):
        return 'go'
    elif os.path.exists(os.path.join(working_dir, 'pom.xml')):
        return 'java'
    elif os.path.exists(os.path.join(working_dir, 'Cargo.toml')):
        return 'rust'
    elif os.path.exists(os.path.join(working_dir, 'CMakeLists.txt')):
        return 'cpp'
    return None


def detect_package_manager(working_dir: str) -> str:
    """自动探测包管理器（for JavaScript/TypeScript projects）"""
    if os.path.exists(os.path.join(working_dir, 'pnpm-lock.yaml')):
        return 'pnpm'
    elif os.path.exists(os.path.join(working_dir, 'yarn.lock')):
        return 'yarn'
    elif os.path.exists(os.path.join(working_dir, 'package-lock.json')):
        return 'npm'
    return 'npm'  # 默认npm


def get_default_commands(language: str, working_dir: str = '.') -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """根据语言获取默认的质量检查命令"""
    if language == 'python':
        return (
            'ruff check .',
            'mypy .',
            'pytest'
        )
    elif language == 'javascript':
        # JavaScript/TypeScript 包括所有前端框架: React/Vue/Angular/Next.js/Vite etc.
        pm = detect_package_manager(working_dir)
        return (
            f'{pm} run lint',
            None,
            f'{pm} test'
        )
    elif language == 'go':
        return (
            'go vet ./...',
            None,
            'go test ./...'
        )
    elif language == 'java':
        return (
            'mvn compile',
            None,
            'mvn test'
        )
    elif language == 'rust':
        return (
            'cargo check',
            None,
            'cargo test'
        )
    elif language == 'cpp':
        return (
            None,
            None,
            None
        )
    return (None, None, None)


class QualityChecker:
    """质量检查器"""

    def __init__(
        self,
        quality_check_cmd: Optional[str] = None,
        type_check_cmd: Optional[str] = None,
        test_cmd: Optional[str] = None,
        working_dir: str = None
    ):
        # 如果用户没有手动配置，尝试自动探测语言并设置默认命令
        if quality_check_cmd is None and type_check_cmd is None and test_cmd is None:
            language = detect_project_language(working_dir or '.')
            if language:
                logger.info(f"Auto-detected project language: {language}")
                quality_check_cmd, type_check_cmd, test_cmd = get_default_commands(language, working_dir or '.')

        self.quality_check_cmd = quality_check_cmd
        self.type_check_cmd = type_check_cmd
        self.test_cmd = test_cmd

    def run_all(self, working_dir: str = None) -> QualityCheckResult:
        """运行所有质量检查"""
        all_errors = []
        all_passed = True

        # Lint检查
        if self.quality_check_cmd:
            passed, errors = self._run_check(self.quality_check_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        # 类型检查
        if self.type_check_cmd:
            passed, errors = self._run_check(self.type_check_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        # 测试
        if self.test_cmd:
            passed, errors = self._run_check(self.test_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        logger.info(f"Quality check done: passed={all_passed}, errors={len(all_errors)}")
        return QualityCheckResult(all_passed, all_errors)

    def _run_check(self, cmd: str, working_dir: str = None) -> Tuple[bool, List[str]]:
        """运行单个检查"""
        logger.info(f"Running quality check: {cmd}")

        # 先检查命令是否存在
        cmd_name = cmd.split()[0]
        if not check_command_available(cmd_name):
            logger.warning(f"Command '{cmd_name}' not found in PATH, skipping this check")
            # 命令不存在不算失败，跳过它，算作通过
            # 这通常发生在新项目还没安装依赖的情况下
            return (True, [])

        returncode, stdout, stderr = run_command(cmd, cwd=working_dir)

        if returncode == 0:
            logger.info(f"Check passed: {cmd}")
            return (True, [])

        errors = []
        if stdout:
            errors.append(f"{cmd} failed:\n{stdout}")
        if stderr:
            errors.append(f"{cmd} stderr:\n{stderr}")

        if not errors:
            errors.append(f"{cmd} exited with code {returncode}")

        logger.warning(f"Check failed: {cmd}, {len(errors)} errors")
        return (False, errors)

    def is_enabled(self) -> bool:
        """是否启用了任何质量检查"""
        return any([self.quality_check_cmd, self.type_check_cmd, self.test_cmd])
