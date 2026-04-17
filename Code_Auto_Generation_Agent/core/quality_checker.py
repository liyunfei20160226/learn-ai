"""质量检查器 - 运行lint、类型检查、测试等，AI动态决定命令"""

import json
import os
from typing import Dict, List, Optional, Tuple

from core.ai_backend import AIBackend
from prompts import get_build_commands_prompt
from utils.logger import get_logger
from utils.subprocess import run_command

logger = get_logger()


class QualityCheckResult:
    """质量检查结果"""
    def __init__(self, passed: bool, errors: List[str], failed_stage: int = 0):
        self.passed = passed
        self.errors = errors
        self.failed_stage = failed_stage  # 在哪一步失败的 (1-4), 0 = 全部完成


def detect_package_manager(working_dir: str) -> str:
    """自动探测包管理器（for JavaScript/TypeScript projects）"""
    if os.path.exists(os.path.join(working_dir, 'pnpm-lock.yaml')):
        return 'pnpm'
    elif os.path.exists(os.path.join(working_dir, 'yarn.lock')):
        return 'yarn'
    elif os.path.exists(os.path.join(working_dir, 'package-lock.json')):
        return 'npm'
    return 'npm'  # 默认npm


class QualityChecker:
    """质量检查器
    所有安装/检查命令完全由AI动态决定，基于项目结构分析。
    第一次检查前调用AI获取命令，之后缓存复用。
    """

    def __init__(
        self,
        working_dir: str = None
    ):
        # 不再接受用户配置，所有命令都由AI动态决定
        self.initial_working_dir = working_dir
        # AI动态获取的命令（缓存）
        self.ai_commands: Optional[Dict[str, List[str]]] = None

    def _parse_ai_response(self, content: str) -> Dict[str, List[str]]:
        """解析AI返回的JSON，提取命令"""
        import re
        # 尝试提取JSON，可能被markdown代码块包围
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)

        try:
            data = json.loads(content)
            result = {
                'install': data.get('install', []),
                'quality_check': data.get('quality_check', []),
                'type_check': data.get('type_check', []),
                'test': data.get('test', []),
            }
            # 确保都是列表
            for k in result:
                if not isinstance(result[k], list):
                    if result[k]:
                        result[k] = [result[k]]
                    else:
                        result[k] = []
            return result
        except Exception as e:
            logger.error(f"解析AI返回的JSON失败: {str(e)}")
            # 返回默认空
            return {
                'install': [],
                'quality_check': [],
                'type_check': [],
                'test': [],
            }

    def run_all(self, working_dir: str = None, ai_backend: Optional[AIBackend] = None, project_description: str = None, start_from_stage: int = 1) -> QualityCheckResult:
        """运行所有质量检查
        如果没有预配置命令，调用AI获取
        逐阶段执行：安装 → 质量检查 → 类型检查 → 测试
        每个阶段失败立即返回，让AI修复后重试，不继续执行后续阶段
        start_from_stage: 从哪个阶段开始执行（用于重试，默认从1开始）
        1 = 安装, 2 = 质量检查, 3 = 类型检查, 4 = 测试
        """
        cwd = working_dir or self.initial_working_dir or '.'
        all_errors = []
        all_passed = True

        # 如果AI已经缓存了命令，直接使用；如果没有，调用AI获取
        has_cached_commands = self.ai_commands is not None

        install_commands: List[str] = []
        quality_check_commands: List[str] = []
        type_check_commands: List[str] = []
        test_commands: List[str] = []

        if has_cached_commands:
            # 使用缓存的AI命令
            install_commands = self.ai_commands.get('install', [])
            quality_check_commands = self.ai_commands.get('quality_check', [])
            type_check_commands = self.ai_commands.get('type_check', [])
            test_commands = self.ai_commands.get('test', [])

        if not has_cached_commands and ai_backend is not None and project_description is not None:
            # 调用AI获取构建命令 - 所有命令都由AI动态决定
            logger.info("正在调用AI获取构建和检查命令（所有命令由AI动态决定）...")
            prompt = get_build_commands_prompt(project_description, cwd)
            # 不需要写入文件，只获取JSON命令
            content = ai_backend.implement_story(prompt, write_files=False)
            commands = self._parse_ai_response(content)
            self.ai_commands = commands

            install_commands = commands.get('install', [])
            quality_check_commands = commands.get('quality_check', [])
            type_check_commands = commands.get('type_check', [])
            test_commands = commands.get('test', [])

            logger.info(f"AI返回: 安装={len(install_commands)} 命令, 质量检查={len(quality_check_commands)}, 类型检查={len(type_check_commands)}, 测试={len(test_commands)}")

        # ========== 阶段1: 安装 ==========
        if start_from_stage <= 1:
            for cmd in install_commands:
                logger.info(f"[阶段1/4 - 安装] 运行: {cmd}")
                returncode, stdout, stderr = run_command(cmd, cwd=cwd)
                if returncode != 0:
                    error_msg = ""
                    if stdout:
                        error_msg += f"{stdout}\n"
                    if stderr:
                        error_msg += stderr
                    all_passed = False
                    all_errors.append(f"安装命令 '{cmd}' 失败:\n{error_msg.strip()}")
                    logger.error(f"安装失败: {cmd}")
                    # 安装失败，立即返回，不继续后续阶段
                    # AI修复后会重试
                    break
                else:
                    logger.info(f"安装完成: {cmd}")

            if not all_passed:
                logger.info(f"质量检查完成: 通过={all_passed}, 错误数={len(all_errors)}")
                return QualityCheckResult(all_passed, all_errors, failed_stage=1)

        # ========== 阶段2: 质量检查 ==========
        # 全部成功后才进入下一阶段
        if start_from_stage <= 2:
            for cmd in quality_check_commands:
                logger.info(f"[阶段2/4 - 质量检查] 运行: {cmd}")
                passed, errors = self._run_single_check(cmd, working_dir)
                if not passed:
                    all_passed = False
                    all_errors.extend(errors)
                    # 质量检查失败，立即返回，不继续后续阶段
                    break

            if not all_passed:
                logger.info(f"质量检查完成: 通过={all_passed}, 错误数={len(all_errors)}")
                return QualityCheckResult(all_passed, all_errors, failed_stage=2)

        # ========== 阶段3: 类型检查 ==========
        if start_from_stage <= 3:
            for cmd in type_check_commands:
                logger.info(f"[阶段3/4 - 类型检查] 运行: {cmd}")
                passed, errors = self._run_single_check(cmd, working_dir)
                if not passed:
                    all_passed = False
                    all_errors.extend(errors)
                    # 类型检查失败，立即返回，不继续后续阶段
                    break

            if not all_passed:
                logger.info(f"质量检查完成: 通过={all_passed}, 错误数={len(all_errors)}")
                return QualityCheckResult(all_passed, all_errors, failed_stage=3)

        # ========== 阶段4: 测试 ==========
        if start_from_stage <= 4:
            for cmd in test_commands:
                logger.info(f"[阶段4/4 - 测试] 运行: {cmd}")
                passed, errors = self._run_single_check(cmd, working_dir)
                if not passed:
                    all_passed = False
                    all_errors.extend(errors)
                    # 测试失败，立即返回
                    break

        logger.info(f"质量检查完成: 通过={all_passed}, 错误数={len(all_errors)}")
        return QualityCheckResult(all_passed, all_errors, failed_stage=0)

    def _run_single_check(self, cmd: str, working_dir: str = None) -> Tuple[bool, List[str]]:
        """运行单个检查"""
        logger.info(f"运行检查命令: {cmd}")
        cwd = working_dir or self.initial_working_dir or '.'

        returncode, stdout, stderr = run_command(cmd, cwd=cwd)

        if returncode == 0:
            logger.info(f"检查通过: {cmd}")
            return (True, [])

        errors = []
        if stdout:
            error_msg = f"{cmd} 失败:\n{stdout}"
            errors.append(error_msg)
            logger.warning(error_msg)
        if stderr:
            error_msg = f"{cmd} 标准错误:\n{stderr}"
            errors.append(error_msg)
            logger.warning(error_msg)

        if not errors:
            error_msg = f"{cmd} 退出码 {returncode}"
            errors.append(error_msg)
            logger.warning(error_msg)

        logger.warning(f"检查失败: {cmd}, {len(errors)} 个错误")
        return (False, errors)

    def is_enabled(self) -> bool:
        """是否启用了任何质量检查
        只要ai_commands有任何命令，就启用检查
        """
        if self.ai_commands is None:
            # 还没调用AI获取命令，第一次检查会调用AI
            return True  # 总是启用，让AI决定
        return (
            len(self.ai_commands.get('install', [])) > 0
            or len(self.ai_commands.get('quality_check', [])) > 0
            or len(self.ai_commands.get('type_check', [])) > 0
            or len(self.ai_commands.get('test', [])) > 0
        )

    def get_ai_commands(self) -> Optional[Dict[str, List[str]]]:
        """获取AI动态生成的命令"""
        return self.ai_commands
