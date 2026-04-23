"""质量检查 + 多轮自动修复编排器

职责：
1. 动态生成质量检查命令
2. 基准检查 + 记录初始错误数
3. 多轮修复循环（调用 FixAgent）
4. 修复后重新检查，判断修复价值
5. 最佳状态保留策略
6. 修复报告生成
7. 状态持久化到 Manifest

依赖方向：SnapshotManager → QualityChecker → FixAgent
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from langchain_openai import ChatOpenAI

from prompts import PromptTemplate, get_prompt_loader

from .agents import FixAgent
from .config import AgentConfig
from .manifest import FixAttempt, FixState, Manifest
from .quality_checker import QualityChecker
from .snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class QualityFixOrchestrator:
    """质量检查与自动修复编排器

    将质量检查流程从 Coordinator 中独立出来，
    专注于"检查 → 修复 → 再检查"的闭环逻辑。
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        working_dir: str | Path,
        config: AgentConfig,
        manifest: Manifest,
        prompts_dir: str = None,
    ):
        self.llm = llm
        self.working_dir = Path(working_dir).resolve()
        self.config = config
        self.manifest = manifest
        self.prompt_loader = get_prompt_loader(prompts_dir)
        self.snapshot_mgr = SnapshotManager(working_dir, manifest.session_id)

    def prepare_check_commands(self, tech_stack_desc: str, project_tree: str) -> Dict[str, list]:
        """生成质量检查命令（并保存到 manifest 避免重复调用）

        Returns:
            {install: [...], lint: [...], type_check: [...], test: [...]}
        """
        # 如果已经生成过，直接复用
        if self.manifest.fix_state and self.manifest.fix_state.check_commands:
            return self.manifest.fix_state.check_commands

        checker = QualityChecker(self.llm, str(self.working_dir), self.config.prompts_dir)
        commands = checker.generate_check_commands(tech_stack_desc, project_tree)

        # 保存到 manifest，避免重复生成
        if self.manifest.fix_state:
            self.manifest.fix_state.check_commands = commands
            self._save_manifest()

        return commands

    def run_quality_check_only(self) -> bool:
        """只运行质量检查，不自动修复（用于快速验证）

        Returns:
            是否全部检查通过
        """
        fix_state = self.manifest.fix_state
        if fix_state is None:
            return False

        checker = QualityChecker(self.llm, str(self.working_dir), self.config.prompts_dir)
        checker.check_commands = fix_state.check_commands

        result = checker.run_all()
        return result.passed

    def run_auto_fix_loop(
        self,
        tech_stack_desc: str,
        project_tree: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """运行完整的质量检查 + 多轮自动修复闭环

        Args:
            tech_stack_desc: 技术栈描述
            project_tree: 项目目录结构树
            progress_callback: 进度回调函数

        Returns:
            修复结果统计
        """
        # ========== 阶段 0: 初始化 ==========
        if self.manifest.fix_state is None:
            self.manifest.fix_state = FixState(
                enabled=True,
                max_attempts=self.config.max_fix_attempts,
                started_at=datetime.now().isoformat(),
            )

        fix_state = self.manifest.fix_state
        checker = QualityChecker(self.llm, str(self.working_dir), self.config.prompts_dir)

        # 复用已生成的检查命令（prepare_check_commands 已保存到 manifest）
        if not fix_state.check_commands:
            fix_state.check_commands = checker.generate_check_commands(tech_stack_desc, project_tree)
        checker.check_commands = fix_state.check_commands

        # ========== 阶段 1: 基准检查 ==========
        if fix_state.current_attempt == 0:
            print("\n📊 运行基准质量检查...")
            result = checker.run_all()
            fix_state.initial_error_count = result.error_count
            fix_state.best_error_count = result.error_count
            fix_state.best_attempt = 0  # 0 代表初始状态
        else:
            # 断点恢复：从上次的最佳状态开始
            snapshot_name = self.snapshot_mgr.get_snapshot_name(fix_state.best_attempt)
            snapshot_exists = self.snapshot_mgr.restore_snapshot(snapshot_name)
            if snapshot_exists:
                print(f"\n🔄 断点恢复，从第 {fix_state.best_attempt} 轮的最佳状态开始")
            else:
                print(f"\n⚠️  快照 {snapshot_name} 不存在，从当前状态继续")
            result = checker.run_all()
            # 更新状态为当前真实的错误状态（避免历史状态与实际不一致）
            fix_state.last_failed_step = result.step_name
            fix_state.last_errors = result.errors or []

        self._save_manifest()

        # 早期成功：如果基准检查已经全部通过，直接返回
        if result.passed:
            print("✅ 所有检查一次性通过，无需修复！")
            fix_state.status = "success"
            fix_state.completed_at = datetime.now().isoformat()
            self._save_manifest()
            self.snapshot_mgr.cleanup_snapshots(keep_list=[])
            return {
                "initial_error_count": fix_state.initial_error_count,
                "final_error_count": 0,
                "fixed_count": 0,
                "attempts": 0,
                "status": "success",
            }

        print(f"⚠️  发现 {result.error_count} 个错误，开始自动修复...")
        initial_snapshot = self.snapshot_mgr.get_snapshot_name(0)
        self.snapshot_mgr.create_snapshot(initial_snapshot)

        # ========== 阶段 2: 多轮修复循环 ==========
        while fix_state.current_attempt < fix_state.max_attempts:
            attempt = fix_state.current_attempt + 1
            print(f"\n{'-'*60}")
            print(f"🔧 第 {attempt}/{fix_state.max_attempts} 轮修复")
            print(f"   当前错误: {result.error_count} 个")
            print(f"   最佳状态: 第 {fix_state.best_attempt} 轮，{fix_state.best_error_count} 个错误")
            print("-"*60)

            # 保存本轮修复前的错误数
            errors_before_fix = result.error_count

            # 1. 创建本轮快照（修复前的状态）
            snapshot_name = self.snapshot_mgr.get_snapshot_name(attempt)
            self.snapshot_mgr.create_snapshot(snapshot_name)

            # 2. 运行修复（内层 Agent 可进行多次自检+修复迭代）
            fix_agent = FixAgent(self.llm, str(self.working_dir), self.config)
            template: PromptTemplate = self.prompt_loader.load("fix_quality_check")
            fix_prompt = template.render(
                step_name=result.step_name,
                errors="\n".join(result.errors),
            )
            finished_normally = fix_agent.run_with_log(fix_prompt, verbose=True)

            # 3. 修复后重新检查（Coordinator 层面的完整验收）
            if finished_normally:
                print(f"\n🔍 第 {attempt} 轮修复完成，重新运行质量检查...")
            else:
                print(f"\n🔍 第 {attempt} 轮修复被强制终止，仍检查结果判断是否有价值...")
            new_result = checker.run_all()

            # 4. 判断这次修复的价值
            improved = new_result.error_count < errors_before_fix

            if new_result.passed:
                print("\n✅🎉 所有检查全部通过！修复成功！")
                fix_state.status = "success"
                fix_state.completed_at = datetime.now().isoformat()
                fix_state.last_failed_step = None
                fix_state.last_errors = []
                # 更新最佳状态
                fix_state.best_attempt = attempt
                fix_state.best_error_count = 0
                result = new_result
                # 记录成功的历史
                fix_state.history.append(FixAttempt(
                    attempt=attempt,
                    failed_step="",
                    errors_before=errors_before_fix,
                    errors_after=0,
                    error_samples=["✅ 所有检查通过，修复成功"],
                    accepted=True,
                    timestamp=datetime.now().isoformat(),
                ))
                fix_state.current_attempt = attempt
                self._save_manifest()
                # 清理：只保留成功状态
                self.snapshot_mgr.cleanup_snapshots(keep_list=[])
                break

            elif improved:
                print(f"✅ 修复有效！错误从 {errors_before_fix} → {new_result.error_count} 个")
                # 更新最佳状态
                if new_result.error_count < fix_state.best_error_count:
                    fix_state.best_attempt = attempt
                    fix_state.best_error_count = new_result.error_count
                # 接受本轮修改，更新 result 为新状态
                result = new_result

            else:
                if new_result.error_count == errors_before_fix:
                    print("⚠️  修复后错误数量无变化，回滚本轮修改")
                else:
                    print("⚠️  修复后错误变多，回滚本轮修改")
                # 回滚到本轮开始前的快照
                self.snapshot_mgr.restore_snapshot(snapshot_name)

            # 5. 记录历史（区分是否被强制终止）
            if not finished_normally:
                error_samples = ["Agent 被强制终止（达到最大迭代次数或超时）"]
                if new_result.errors:
                    error_samples.extend(new_result.errors[:4])
            else:
                error_samples = new_result.errors[:5] if new_result.errors else []

            fix_state.history.append(FixAttempt(
                attempt=attempt,
                failed_step=new_result.step_name or "",
                errors_before=errors_before_fix,
                errors_after=new_result.error_count,
                error_samples=error_samples,
                accepted=improved,
                timestamp=datetime.now().isoformat(),
            ))
            fix_state.current_attempt = attempt
            fix_state.last_failed_step = new_result.step_name
            fix_state.last_errors = new_result.errors or []
            fix_state.status = "running"
            self._save_manifest()

        # ========== 阶段 3: 达到最大次数，收尾 ==========
        if not result.passed:
            print(f"\n{'-'*60}")
            print(f"⚠️  已达到最大修复次数 ({fix_state.max_attempts})")
            print("-"*60)

            # 恢复到最佳状态
            if fix_state.best_attempt > 0:
                snapshot_name = self.snapshot_mgr.get_snapshot_name(fix_state.best_attempt)
                self.snapshot_mgr.restore_snapshot(snapshot_name)
                print(f"🔄 已恢复到最佳状态（第 {fix_state.best_attempt} 轮，{fix_state.best_error_count} 个错误）")
                fix_state.status = "partial_success"
            else:
                print("⚠️  修复没有改善，保留原始状态")
                self.snapshot_mgr.restore_snapshot(initial_snapshot)
                fix_state.status = "failed"

            # 清理所有快照
            self.snapshot_mgr.cleanup_snapshots(keep_list=[])

            fix_state.completed_at = datetime.now().isoformat()
            self._save_manifest()

        # ========== 输出修复报告 ==========
        total_fixed = fix_state.initial_error_count - fix_state.best_error_count
        print(f"\n{'='*60}")
        print("📊 自动修复总结报告")
        print(f"   初始错误: {fix_state.initial_error_count} 个")
        print(f"   最终错误: {fix_state.best_error_count} 个")
        print(f"   成功修复: {total_fixed} 个错误")
        print(f"   修复轮次: {fix_state.current_attempt} 轮")
        print(f"   修复状态: {fix_state.status}")
        print(f"{'='*60}\n")

        return {
            "initial_error_count": fix_state.initial_error_count,
            "final_error_count": fix_state.best_error_count,
            "fixed_count": total_fixed,
            "attempts": fix_state.current_attempt,
            "status": fix_state.status,
        }

    def _save_manifest(self) -> None:
        """保存 manifest 状态（原子写入，委托给 Manifest.save）"""
        manifest_path = self.working_dir / ".codegen_manifest.json"
        self.manifest.save(manifest_path)
