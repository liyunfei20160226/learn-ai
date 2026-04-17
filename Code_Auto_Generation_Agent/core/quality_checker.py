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
        # 如果用户手动配置了，直接使用
        self.configured_quality_check_cmd = quality_check_cmd
        self.configured_type_check_cmd = type_check_cmd
        self.configured_test_cmd = test_cmd
        self.initial_working_dir = working_dir

    def run_all(self, working_dir: str = None) -> QualityCheckResult:
        """运行所有质量检查"""
        # 自动探测：如果没有手动配置，在运行前探测（此时AI已经生成了文件）
        cwd = working_dir or self.initial_working_dir or '.'
        quality_check_cmd = self.configured_quality_check_cmd
        type_check_cmd = self.configured_type_check_cmd
        test_cmd = self.configured_test_cmd

        if quality_check_cmd is None and type_check_cmd is None and test_cmd is None:
            language = detect_project_language(cwd)
            if language:
                logger.info(f"自动探测到项目语言: {language}")
                quality_check_cmd, type_check_cmd, test_cmd = get_default_commands(language, cwd)

        all_errors = []
        all_passed = True

        # Lint检查
        if quality_check_cmd:
            passed, errors = self._run_check(quality_check_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        # 类型检查
        if type_check_cmd:
            passed, errors = self._run_check(type_check_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        # 测试
        if test_cmd:
            passed, errors = self._run_check(test_cmd, working_dir)
            if not passed:
                all_passed = False
                all_errors.extend(errors)

        logger.info(f"质量检查完成: 通过={all_passed}, 错误数={len(all_errors)}")
        return QualityCheckResult(all_passed, all_errors)

    def _run_check(self, cmd: str, working_dir: str = None) -> Tuple[bool, List[str]]:
        """运行单个检查"""
        logger.info(f"运行质量检查: {cmd}")

        # 先检查命令是否存在
        cmd_name = cmd.split()[0]
        if not check_command_available(cmd_name):
            # 只要配置了检查命令但命令不存在，就标记为失败
            # 需要用户安装好依赖/工具后，用 --resume 重新运行检查
            cwd = working_dir or os.getcwd()
            # 给出具体的安装提示，根据项目类型
            if os.path.exists(os.path.join(cwd, 'pyproject.toml')):
                hint = (
                    f"需要的命令 '{cmd_name}' 找不到。\n"
                    f"请先在目录 {cwd} 安装依赖:\n"
                    f"示例: 'uv sync' 或 'pip install -r requirements.txt'\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            elif os.path.exists(os.path.join(cwd, 'package.json')):
                pm = detect_package_manager(cwd)
                hint = (
                    f"需要的命令 '{cmd_name}' 找不到。\n"
                    f"请先在目录 {cwd} 安装依赖: '{pm} install'\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            elif os.path.exists(os.path.join(cwd, 'requirements.txt')):
                hint = (
                    f"需要的命令 '{cmd_name}' 找不到。\n"
                    f"请先在目录 {cwd} 安装依赖: 'pip install -r requirements.txt'\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            elif os.path.exists(os.path.join(cwd, 'pom.xml')):
                hint = (
                    f"需要的命令 '{cmd_name}' 找不到。\n"
                    f"请先安装 Maven 并在目录 {cwd} 运行 'mvn install'\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            elif os.path.exists(os.path.join(cwd, 'Cargo.toml')):
                hint = (
                    f"需要的命令 '{cmd_name}' 找不到。\n"
                    f"请先安装 Rust 并在目录 {cwd} 运行 'cargo build'\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            else:
                hint = (
                    f"需要的命令 '{cmd_name}' 在PATH中找不到。\n"
                    f"请在目录 {cwd} 安装所需工具或依赖\n"
                    f"安装完成后使用 --resume 参数重新运行继续。"
                )
            logger.error(hint)
            return (False, [hint])

        returncode, stdout, stderr = run_command(cmd, cwd=working_dir)

        if returncode == 0:
            logger.info(f"检查通过: {cmd}")
            return (True, [])

        errors = []
        if stdout:
            errors.append(f"{cmd} 失败:\n{stdout}")
        if stderr:
            errors.append(f"{cmd} 标准错误:\n{stderr}")

        if not errors:
            errors.append(f"{cmd} 退出码 {returncode}")

        logger.warning(f"检查失败: {cmd}, {len(errors)} 个错误")
        return (False, errors)

    def is_enabled(self) -> bool:
        """是否启用了任何质量检查"""
        return any([self.configured_quality_check_cmd, self.configured_type_check_cmd, self.configured_test_cmd])
