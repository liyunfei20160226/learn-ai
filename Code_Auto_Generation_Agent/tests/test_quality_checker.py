"""测试质量检查器"""

from unittest.mock import MagicMock, patch

import pytest

from core.quality_checker import CheckResult, QualityChecker, _ensure_list


@pytest.fixture(autouse=True)
def mock_prompts():
    """Mock 所有 prompt 模板加载"""
    with patch("core.quality_checker.get_prompt_loader") as mock_loader_cls:
        mock_loader = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "check this"
        mock_loader.load.return_value = mock_template
        mock_loader_cls.return_value = mock_loader
        yield


def test_ensure_list_with_list():
    """测试列表直接返回"""
    assert _ensure_list(["a", "b"]) == ["a", "b"]
    assert _ensure_list([]) == []


def test_ensure_list_with_string():
    """测试字符串转为单元素列表"""
    assert _ensure_list("hello") == ["hello"]
    assert _ensure_list("  hello  ") == ["hello"]


def test_ensure_list_with_empty_string():
    """测试空字符串转为默认列表"""
    assert _ensure_list("") == []
    assert _ensure_list("   ") == []


def test_ensure_list_with_none():
    """测试 None 转为默认列表"""
    assert _ensure_list(None) == []
    assert _ensure_list(None, default=["default"]) == ["default"]


def test_ensure_list_with_other_types():
    """测试其他类型转为默认列表"""
    assert _ensure_list(123) == []
    assert _ensure_list({}) == []


def test_check_result_defaults():
    """测试 CheckResult 默认值"""
    result = CheckResult(passed=True)
    assert result.passed is True
    assert result.failed_step is None
    assert result.errors == []
    assert result.step_name is None
    assert result.error_count == 0


def test_check_result_with_failure():
    """测试失败的 CheckResult"""
    result = CheckResult(
        passed=False,
        failed_step=1,
        errors=["error1", "error2"],
        step_name="lint",
        error_count=5,
    )
    assert result.passed is False
    assert result.failed_step == 1
    assert len(result.errors) == 2
    assert result.step_name == "lint"
    assert result.error_count == 5


def test_quality_checker_init():
    """测试初始化"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")

    assert checker.llm == mock_llm
    assert checker.working_dir == "/tmp/work"
    assert checker.check_commands == {}


def test_quality_checker_generate_check_commands_success():
    """测试成功生成检查命令"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = """
    {
        "install": ["pip install -e ."],
        "lint": ["ruff check ."],
        "type_check": ["mypy ."],
        "test": ["pytest tests/"]
    }
    """
    mock_llm.invoke.return_value = mock_response

    checker = QualityChecker(mock_llm, "/tmp/work")
    commands = checker.generate_check_commands("Python 3.11 + FastAPI", "src/main.py")

    assert commands["install"] == ["pip install -e ."]
    assert commands["lint"] == ["ruff check ."]
    assert commands["type_check"] == ["mypy ."]
    assert commands["test"] == ["pytest tests/"]
    assert checker.check_commands == commands


def test_quality_checker_generate_check_commands_json_error():
    """测试 JSON 解析失败时的降级处理"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "not a json"
    mock_llm.invoke.return_value = mock_response

    checker = QualityChecker(mock_llm, "/tmp/work")
    commands = checker.generate_check_commands("Python", "main.py")

    assert commands["install"] == []
    assert commands["lint"] == []
    assert commands["type_check"] == []
    assert commands["test"] == []


def test_quality_checker_run_step_no_commands():
    """测试没有命令时直接成功"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")

    success, errors, count = checker.run_step("lint")
    assert success is True
    assert errors == []
    assert count == 0


def test_quality_checker_run_step_success():
    """测试步骤执行成功"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {"lint": ["echo ok"]}

    with patch.object(checker, "_run_command", return_value=(True, "ok")):
        success, errors, count = checker.run_step("lint")

    assert success is True
    assert errors == []
    assert count == 0


def test_quality_checker_run_step_failure():
    """测试步骤执行失败"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {"lint": ["bad_cmd"]}

    with patch.object(checker, "_run_command", return_value=(False, "error1\nerror2\n")):
        success, errors, count = checker.run_step("lint")

    assert success is False
    assert len(errors) == 1
    assert "bad_cmd" in errors[0]
    assert count == 2  # 2 行错误输出


def test_quality_checker_run_step_failure_no_output():
    """测试失败但无错误输出"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {"lint": ["bad_cmd"]}

    # 失败但输出为空
    with patch.object(checker, "_run_command", return_value=(False, "")):
        success, errors, count = checker.run_step("lint")

    assert success is False
    assert count == 1  # 至少算 1 个错误


def test_quality_checker_run_all_success():
    """测试所有步骤成功"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {
        "lint": ["ruff check"],
        "test": ["pytest"],
    }

    with patch.object(checker, "_run_command", return_value=(True, "")):
        result = checker.run_all()

    assert result.passed is True
    assert result.failed_step is None
    assert result.error_count == 0


def test_quality_checker_run_all_failure_at_step_1():
    """测试在第二个步骤失败"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {
        "install": ["pip install"],
        "lint": ["ruff check"],
        "test": ["pytest"],
    }

    call_count = 0

    def mock_run(cmd):
        nonlocal call_count
        call_count += 1
        if cmd == "ruff check":
            return False, "lint error"
        return True, ""

    with patch.object(checker, "_run_command", side_effect=mock_run):
        result = checker.run_all()

    assert result.passed is False
    assert result.failed_step == 1  # lint 是第 1 步（0 开始）
    assert result.step_name == "lint"


def test_quality_checker_run_all_start_from():
    """测试从指定步骤开始"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")
    checker.check_commands = {
        "install": ["pip install"],
        "lint": ["ruff check"],
        "test": ["pytest"],
    }

    call_count = 0

    def mock_run(cmd):
        nonlocal call_count
        call_count += 1
        return True, ""

    with patch.object(checker, "_run_command", side_effect=mock_run):
        result = checker.run_all(start_from=2)  # 直接从 test 开始

    assert result.passed is True
    assert call_count == 1  # 只执行了 test 步骤


def test_quality_checker_get_step_name():
    """测试获取步骤名称"""
    mock_llm = MagicMock()
    checker = QualityChecker(mock_llm, "/tmp/work")

    assert checker.get_step_name(0) == "依赖安装"
    assert checker.get_step_name(1) == "代码检查"
    assert checker.get_step_name(2) == "类型检查"
    assert checker.get_step_name(3) == "测试执行"
    assert checker.get_step_name(-1) == ""
    assert checker.get_step_name(100) == ""
