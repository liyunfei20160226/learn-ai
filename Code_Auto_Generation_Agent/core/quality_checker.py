"""质量检查器 - 运行lint、类型检查、测试等"""

from typing import List, Tuple, Optional
from utils.subprocess import run_command
from utils.logger import get_logger


logger = get_logger()


class QualityCheckResult:
    """质量检查结果"""
    def __init__(self, passed: bool, errors: List[str]):
        self.passed = passed
        self.errors = errors


class QualityChecker:
    """质量检查器"""

    def __init__(
        self,
        quality_check_cmd: Optional[str] = None,
        type_check_cmd: Optional[str] = None,
        test_cmd: Optional[str] = None
    ):
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
