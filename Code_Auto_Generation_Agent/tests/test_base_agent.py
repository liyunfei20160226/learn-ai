"""测试 Agent 基类

注意：BaseAgent 是抽象类，需要创建简单的测试子类来测试。
"""

from collections import Counter
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from core.agents.base_agent import (
    _LIST_FIELDS,
    _STATUS_REPORT_MARKER,
    BaseAgent,
    _build_status_report,
    _merge_state_value,
)


def test_merge_state_value_messages():
    """测试合并 messages 字段"""
    full_state: Dict[str, Any] = {"messages": []}
    new_messages = [AIMessage(content="msg1"), AIMessage(content="msg2")]

    _merge_state_value(full_state, "messages", new_messages)

    assert len(full_state["messages"]) == 2
    assert full_state["messages"][0].content == "msg1"


def test_merge_state_value_messages_invalid_type():
    """测试 messages 类型错误"""
    full_state: Dict[str, Any] = {"messages": []}

    with pytest.raises(TypeError, match="必须返回 list"):
        _merge_state_value(full_state, "messages", "not a list")


def test_merge_state_value_messages_invalid_element():
    """测试 messages 元素类型错误"""
    full_state: Dict[str, Any] = {"messages": []}

    with pytest.raises(TypeError, match="元素必须是 BaseMessage"):
        _merge_state_value(full_state, "messages", ["not a message"])


def test_merge_state_value_list_fields():
    """测试合并列表字段"""
    for field in _LIST_FIELDS:
        full_state: Dict[str, Any] = {field: ["a"]}
        _merge_state_value(full_state, field, ["b", "c"])
        assert full_state[field] == ["a", "b", "c"]


def test_merge_state_value_list_invalid_type():
    """测试列表字段类型错误"""
    with pytest.raises(TypeError, match="必须返回 list"):
        _merge_state_value({}, "key_decisions", "not a list")


def test_merge_state_value_scalar_fields():
    """测试标量字段直接覆盖"""
    full_state: Dict[str, Any] = {"iteration": 1, "working_summary": "old"}

    _merge_state_value(full_state, "iteration", 2)
    _merge_state_value(full_state, "working_summary", "new summary")

    assert full_state["iteration"] == 2
    assert full_state["working_summary"] == "new summary"


def test_build_status_report_empty():
    """测试没有状态信息时返回 None"""
    state = {}
    result = _build_status_report(state)
    assert result is None


def test_build_status_report_with_summary():
    """测试只包含工作摘要"""
    state = {"working_summary": "完成了数据库设计"}
    result = _build_status_report(state)
    assert result is not None
    assert _STATUS_REPORT_MARKER in result
    assert "工作摘要" in result
    assert "数据库设计" in result


def test_build_status_report_with_all_fields():
    """测试包含所有字段"""
    state = {
        "working_summary": "阶段进展良好",
        "key_decisions": ["使用 FastAPI", "使用 PostgreSQL"],
        "completed_subtasks": ["数据库模型", "API 路由"],
        "context_warnings": ["上下文接近上限"],
    }
    result = _build_status_report(state)

    assert "关键决策" in result
    assert "已完成子任务" in result
    assert "上下文告警" in result
    assert "FastAPI" in result
    assert "API 路由" in result
    assert "上下文接近上限" in result


# 创建一个测试用的具体 Agent 子类
class TestAgent(BaseAgent):
    """测试用的 Agent 子类"""

    def _init_tools(self) -> List:
        return []

    def _get_prompt_template_name(self) -> str:
        return "test_template"  # 实际不存在，测试时 mock


def test_base_agent_initialization():
    """测试 Agent 初始化"""
    mock_llm = MagicMock()
    mock_config = MagicMock()
    mock_config.prompts_dir = None
    mock_config.max_iterations = 50
    mock_config.openai_timeout = 120

    agent = TestAgent(mock_llm, "/tmp/work", mock_config)

    assert agent.llm == mock_llm
    assert agent.working_dir == "/tmp/work"
    assert agent.config == mock_config
    assert agent.role_name == "Test"
    assert len(agent.tools) == 4  # 基类的 4 个工具


def test_base_agent_get_tool_call_counts():
    """测试统计工具调用次数"""
    result = {
        "tools_called": ["read_file", "write_file", "read_file", "finish", "read_file"]
    }
    counts = BaseAgent.get_tool_call_counts(result)

    assert counts["read_file"] == 3
    assert counts["write_file"] == 1
    assert counts["finish"] == 1


def test_base_agent_get_tool_call_counts_empty():
    """测试空工具调用列表"""
    counts = BaseAgent.get_tool_call_counts({})
    assert counts == {}


def test_base_agent_get_last_message():
    """测试获取最后一条消息"""
    result = {
        "messages": [
            SystemMessage(content="system"),
            HumanMessage(content="hello"),
            AIMessage(content="answer"),
        ]
    }
    msg = BaseAgent.get_last_message(result)
    assert msg == "answer"


def test_base_agent_get_last_message_empty():
    """测试没有消息时"""
    msg = BaseAgent.get_last_message({})
    assert msg == ""


def test_base_agent_run_with_exception():
    """测试异常情况下返回部分状态"""
    mock_llm = MagicMock()
    mock_config = MagicMock()
    mock_config.prompts_dir = None
    mock_config.max_iterations = 10
    mock_config.openai_timeout = 120

    agent = TestAgent(mock_llm, "/tmp/work", mock_config)

    # 先 mock prompt_loader.load，再 mock graph.stream
    with patch.object(agent.prompt_loader, "load") as mock_load:
        mock_template = MagicMock()
        mock_template.render.return_value = "system prompt"
        mock_load.return_value = mock_template

        # 让 graph.stream 抛出异常
        with patch.object(agent.graph, "stream", side_effect=RuntimeError("test error")):
            result = agent.run("test input")

    # 即使异常也应该返回状态
    assert "context_warnings" in result
    assert any("执行异常" in w for w in result["context_warnings"])
    assert "RuntimeError" in str(result["context_warnings"])


def test_base_agent_default_tool_callback(capsys):
    """测试默认工具回调的输出"""
    # 测试写文件
    BaseAgent.default_tool_callback("tools", "write_file", "file.py")
    captured = capsys.readouterr()
    assert "📝" in captured.out

    # 测试读文件
    BaseAgent.default_tool_callback("tools", "read_file", "file.py")
    captured = capsys.readouterr()
    assert "📄" in captured.out

    # 测试完成任务
    BaseAgent.default_tool_callback("tools", "finish", "done")
    captured = capsys.readouterr()
    assert "🏁" in captured.out


def test_base_agent_initial_state():
    """测试初始状态结构"""
    mock_llm = MagicMock()
    mock_config = MagicMock()
    mock_config.prompts_dir = None
    mock_config.max_iterations = 50
    mock_config.openai_timeout = 120

    agent = TestAgent(mock_llm, "/tmp/work", mock_config)

    # 模拟 run 方法中的 initial_state 创建
    # 但不实际执行
    with patch.object(agent.graph, "stream", return_value=[]):
        with patch.object(agent.prompt_loader, "load") as mock_load:
            mock_template = MagicMock()
            mock_template.render.return_value = "system prompt"
            mock_load.return_value = mock_template

            result = agent.run("test input")

    assert "messages" in result
    assert "iteration" in result
    assert "start_time" in result
    assert "tools_called" in result
    assert "key_decisions" in result
    assert "completed_subtasks" in result
    assert "working_summary" in result


import pytest
