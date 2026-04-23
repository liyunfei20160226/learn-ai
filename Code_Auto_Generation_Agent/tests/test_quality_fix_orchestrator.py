"""测试质量修复编排器"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.manifest import FixState, Manifest
from core.quality_fix_orchestrator import QualityFixOrchestrator


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.max_fix_attempts = 5
    config.prompts_dir = None
    return config


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_manifest():
    return Manifest.create(project_name="test-project")


@pytest.fixture
def mock_prompts():
    """Mock 所有 prompt 模板加载"""
    with patch("core.quality_fix_orchestrator.get_prompt_loader") as mock_loader_cls:
        mock_loader = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "fix this error"
        mock_loader.load.return_value = mock_template
        mock_loader_cls.return_value = mock_loader
        yield


class TestQualityFixOrchestratorInit:
    """测试初始化"""

    def test_init_basic(self, temp_dir, mock_config, sample_manifest):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(
            llm=mock_llm,
            working_dir=temp_dir,
            config=mock_config,
            manifest=sample_manifest,
        )

        assert orchestrator.llm == mock_llm
        assert orchestrator.working_dir == temp_dir.resolve()
        assert orchestrator.config == mock_config
        assert orchestrator.manifest == sample_manifest
        assert orchestrator.snapshot_mgr is not None


class TestPrepareCheckCommands:
    """测试生成检查命令"""

    def test_prepare_check_commands_first_time(self, temp_dir, mock_config, sample_manifest):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        # Mock QualityChecker
        mock_checker = MagicMock()
        mock_checker.generate_check_commands.return_value = {
            "lint": ["ruff check ."],
            "type_check": ["mypy ."],
        }

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            commands = orchestrator.prepare_check_commands("Python", "src/")

        assert commands["lint"] == ["ruff check ."]
        assert commands["type_check"] == ["mypy ."]
        mock_checker.generate_check_commands.assert_called_once()

    def test_prepare_check_commands_reuse_from_manifest(self, temp_dir, mock_config, sample_manifest):
        """测试复用已保存在 manifest 中的检查命令"""
        sample_manifest.fix_state = FixState(
            check_commands={"lint": ["cached lint cmd"], "type_check": ["cached mypy cmd"]}
        )

        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        commands = orchestrator.prepare_check_commands("Python", "src/")

        # 应该使用缓存，不重新生成
        assert commands["lint"] == ["cached lint cmd"]
        assert commands["type_check"] == ["cached mypy cmd"]


class TestRunQualityCheckOnly:
    """测试只运行质量检查"""

    def test_run_quality_check_only_no_fix_state(self, temp_dir, mock_config, sample_manifest):
        """没有 fix_state 时返回 False"""
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        result = orchestrator.run_quality_check_only()
        assert result is False

    def test_run_quality_check_only_with_checker(self, temp_dir, mock_config, sample_manifest):
        """测试运行检查并返回结果"""
        sample_manifest.fix_state = FixState(
            check_commands={"lint": ["ruff check ."]}
        )

        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        mock_checker = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = True
        mock_checker.run_all.return_value = mock_result

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            result = orchestrator.run_quality_check_only()

        assert result is True


class TestAutoFixLoopEarlySuccess:
    """测试修复循环 - 基准检查直接通过"""

    def test_early_success_when_no_errors(self, temp_dir, mock_config, sample_manifest):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        mock_checker = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.error_count = 0
        mock_checker.run_all.return_value = mock_result
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots") as mock_cleanup:
                result = orchestrator.run_auto_fix_loop("Python", "src/")

        assert result["status"] == "success"
        assert result["initial_error_count"] == 0
        assert result["final_error_count"] == 0
        assert result["fixed_count"] == 0
        assert result["attempts"] == 0
        mock_cleanup.assert_called_once()


class TestAutoFixLoopFullSuccess:
    """测试修复循环 - 多轮后完全成功"""

    def test_fix_loop_complete_success(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        # 第一轮检查失败，第二轮修复后通过
        call_state = {"count": 0}

        def mock_run_all():
            call_state["count"] += 1
            result = MagicMock()
            if call_state["count"] == 1:
                result.passed = False
                result.error_count = 10
                result.step_name = "lint"
                result.errors = ["error1", "error2"]
            else:
                result.passed = True
                result.error_count = 0
            return result

        mock_checker = MagicMock()
        mock_checker.run_all.side_effect = mock_run_all
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = True

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot"):
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            result = orchestrator.run_auto_fix_loop("Python", "src/")

        assert result["status"] == "success"
        assert result["attempts"] == 1
        assert result["initial_error_count"] == 10
        assert result["final_error_count"] == 0


class TestAutoFixLoopImprovedButNotPerfect:
    """测试修复循环 - 有改进但未完全成功"""

    def test_fix_loop_improved(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        call_count = 0

        def mock_run_all():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.passed = False
            result.step_name = "lint"
            result.errors = ["error"]
            # 每次修复后错误数减少但不为0
            if call_count == 1:
                result.error_count = 10  # 初始
            elif call_count == 2:
                result.error_count = 5   # 第1轮后
            else:
                result.error_count = 3   # 第2轮后
            return result

        mock_checker = MagicMock()
        mock_checker.run_all = mock_run_all
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = True

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot"):
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            result = orchestrator.run_auto_fix_loop("Python", "src/")

        # 达到最大次数后应该是 partial_success
        assert result["status"] == "partial_success"
        assert result["initial_error_count"] == 10
        assert result["final_error_count"] == 3
        assert result["fixed_count"] == 7


class TestAutoFixLoopNoImprovement:
    """测试修复循环 - 越修越糟，回滚"""

    def test_fix_loop_regression_rollback(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        call_count = 0

        def mock_run_all():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.passed = False
            result.step_name = "lint"
            result.errors = ["error"]
            if call_count == 1:
                result.error_count = 5   # 初始
            else:
                result.error_count = 15  # 修复后变糟了
            return result

        mock_checker = MagicMock()
        mock_checker.run_all = mock_run_all
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = True

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot") as mock_restore:
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            result = orchestrator.run_auto_fix_loop("Python", "src/")

        # 应该回滚到初始状态
        assert result["status"] == "failed"
        assert result["fixed_count"] == 0
        # 应该调用 restore_snapshot 回滚
        mock_restore.assert_called()


class TestAutoFixLoopResumeFromBreakpoint:
    """测试断点恢复功能"""

    def test_resume_from_breakpoint_with_best_state(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        sample_manifest.fix_state = FixState(
            current_attempt=2,
            max_attempts=5,
            best_attempt=1,
            best_error_count=5,
            initial_error_count=10,
        )

        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        mock_checker = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = False
        mock_result.error_count = 5
        mock_result.step_name = "lint"
        mock_result.errors = ["error"]
        mock_checker.run_all.return_value = mock_result
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = True

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot", return_value=True):
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            result = orchestrator.run_auto_fix_loop("Python", "src/")

        # 从第2轮恢复，应该继续尝试
        assert result["attempts"] == 5  # max_attempts = 5
        assert result["initial_error_count"] == 10


class TestAutoFixLoopAgentTerminated:
    """测试 Agent 被强制终止时的处理"""

    def test_agent_force_terminated_still_records(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        call_count = 0

        def mock_run_all():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.passed = False
            result.error_count = 5
            result.step_name = "lint"
            result.errors = ["error"]
            return result

        mock_checker = MagicMock()
        mock_checker.run_all = mock_run_all
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        # Agent 返回 False 表示被强制终止
        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = False

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot"):
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            orchestrator.run_auto_fix_loop("Python", "src/")

        # 应该记录了历史
        assert sample_manifest.fix_state is not None
        assert len(sample_manifest.fix_state.history) > 0
        # 应该有被强制终止的错误样例
        last_attempt = sample_manifest.fix_state.history[-1]
        assert "强制终止" in last_attempt.error_samples[0]


class TestFixStatePersists:
    """测试 FixState 状态在修复过程中被正确更新"""

    def test_fix_state_updated_during_fix(self, temp_dir, mock_config, sample_manifest, mock_prompts):
        mock_llm = MagicMock()
        orchestrator = QualityFixOrchestrator(mock_llm, temp_dir, mock_config, sample_manifest)

        call_count = 0

        def mock_run_all():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            result.passed = False
            result.step_name = "lint"
            result.errors = ["error"]
            if call_count == 1:
                result.error_count = 10
            else:
                result.error_count = 7
            return result

        mock_checker = MagicMock()
        mock_checker.run_all = mock_run_all
        mock_checker.generate_check_commands.return_value = {"lint": ["ruff"]}

        mock_fix_agent = MagicMock()
        mock_fix_agent.run_with_log.return_value = True

        with patch("core.quality_fix_orchestrator.QualityChecker", return_value=mock_checker):
            with patch("core.quality_fix_orchestrator.FixAgent", return_value=mock_fix_agent):
                with patch.object(orchestrator.snapshot_mgr, "create_snapshot"):
                    with patch.object(orchestrator.snapshot_mgr, "restore_snapshot"):
                        with patch.object(orchestrator.snapshot_mgr, "cleanup_snapshots"):
                            orchestrator.run_auto_fix_loop("Python", "src/")

        fix_state = sample_manifest.fix_state
        assert fix_state is not None
        assert fix_state.initial_error_count == 10
        assert fix_state.best_error_count == 7
        assert fix_state.current_attempt == 5
        assert len(fix_state.history) == 5  # 5 轮都有记录
        assert fix_state.last_failed_step == "lint"
        assert len(fix_state.last_errors) > 0
