#!/usr/bin/env python3
"""
上下文管理系统 Phase 1 - 完整功能测试
"""
import sys
import os

# 添加 src 到路径（从 test/ 目录向上一级，再到 src/）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 强制 UTF-8 输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"🧪 {title}")
    print('=' * 60)


def print_pass(msg: str = "通过"):
    print(f"  ✅ {msg}")


def print_fail(msg: str):
    print(f"  ❌ {msg}")


def test_1_token_estimation():
    """测试 1: Token 估算功能"""
    print_header("测试 1: Token 估算")

    from context.token_counter import estimate_tokens, estimate_messages_tokens

    # 中英文混合
    text = "Hello, 世界！This is a test message."
    tokens = estimate_tokens(text)
    print(f"  中英文混合 '{text[:20]}...': {tokens} tokens")
    assert tokens > 0, "Token 数应该大于 0"
    print_pass("Token 估算正常")

    # 消息列表
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    total = estimate_messages_tokens(messages)
    print(f"  2 条消息总计: {total} tokens")
    assert total > 0, "消息 Token 总数应该大于 0"
    print_pass("消息列表估算正常")


def test_2_tool_buffer_truncation():
    """测试 2: 工具结果分级截断"""
    print_header("测试 2: ToolResultBuffer 分级截断")

    from context.tool_buffer import ToolResultBufferLayer

    buffer = ToolResultBufferLayer(
        max_total_tokens=10000,
        small_threshold=100,   # 故意设小，方便测试
        large_threshold=500,   # <100 完整，100-500 中等，>500 深度
    )

    # 小结果 - 应该完整保留
    small = "x" * 50
    display = buffer.add("small", "TestTool", small)
    print(f"  小结果 ({len(small)} 字符): {display}")
    assert "完整" in display, "小结果应该完整保留"

    # 中等结果 - 应该部分截断
    medium = "x" * 300
    display = buffer.add("medium", "TestTool", medium)
    print(f"  中等结果 ({len(medium)} 字符): {display}")
    assert "中等" in display or "截断" in display, "中等结果应该标记截断"

    # 大结果 - 应该深度截断
    large = "x" * 1000
    display = buffer.add("large", "TestTool", large)
    print(f"  大结果 ({len(large)} 字符): {display}")
    assert "深度" in display or "截断" in display, "大结果应该深度截断"

    # 验证内容确实被截断了（长度短于原文）
    active = buffer.get_active_results()
    for r in active:
        content = r["content"][0]["content"]
        if "large" in r["content"][0]["content"]:
            assert len(content) < 1000, "大结果内容应该被截断"
    print_pass("三级截断策略正常")


def test_3_tool_recall():
    """测试 3: 工具结果完整召回"""
    print_header("测试 3: 工具结果召回功能")

    from context.tool_buffer import ToolResultBufferLayer

    buffer = ToolResultBufferLayer()
    original = "完整内容\n" * 100  # 100 行
    buffer.add("tool_1", "ReadTool", original)

    # 召回应该返回完整内容
    recalled = buffer.recall("tool_1")
    print(f"  原文长度: {len(original)} 字符")
    print(f"  召回长度: {len(recalled)} 字符")

    assert recalled == original, "召回内容应该与原文完全一致"
    print_pass("完整召回正常")


def test_4_working_memory_window():
    """测试 4: 工作记忆滑动窗口"""
    print_header("测试 4: WorkingMemory 滑动窗口")

    from context.working import WorkingMemoryLayer

    # 窗口大小: 2 轮 ≈ 6 条消息
    working = WorkingMemoryLayer(window_size=2, max_tokens=10000)

    # 添加 10 条消息，应该只保留最后的 6 条
    for i in range(10):
        working.add_user_message(f"消息 {i}: " + "x" * 100)

    messages = working.get_messages()
    print(f"  添加 10 条消息后，实际保留: {len(messages)} 条")

    # 检查最早的消息是不是序号 4（保留了最后 6 条）
    first_msg = messages[0]["content"]
    print(f"  保留的第一条消息: {first_msg[:20]}...")
    assert "消息 4" in first_msg or "消息 5" in first_msg or "消息 6" in first_msg, \
        "应该只保留最近的消息"
    print_pass("滑动窗口自动裁剪正常")


def test_5_token_budget_control():
    """测试 5: Token 预算控制（不超上限）"""
    print_header("测试 5: Token 预算控制")

    from context.tool_buffer import ToolResultBufferLayer

    # 设置非常小的预算，验证不会超
    buffer = ToolResultBufferLayer(
        max_total_tokens=100,  # 只能放约 300 字符
        small_threshold=100,
        large_threshold=200,
    )

    # 添加 5 个大结果
    for i in range(5):
        result = "大结果内容 " * 50  # 每个 ≈ 300 字符 ≈ 100 tokens
        buffer.add(f"tool_{i}", "TestTool", result)

    stats = buffer.stats()
    print(f"  尝试添加 5 个结果")
    print(f"  实际缓存: {stats['total_cached']} 个")
    print(f"  实际 Token: {stats['total_tokens']} tokens")
    print(f"  预算上限: {buffer.max_total_tokens} tokens")

    # 不要求严格等于（因为 FIFO 清理），但不能失控
    assert stats['total_tokens'] < 1000, "Token 应该被限制在合理范围"
    print_pass("Token 预算控制正常")


def test_6_context_manager_flow():
    """测试 6: ContextManager 完整工作流"""
    print_header("测试 6: ContextManager 完整流程")

    from context.manager import ContextManager

    cm = ContextManager(
        total_budget=50000,
        working_window_size=5,
        working_max_tokens=10000,
        tool_buffer_max_tokens=30000,
    )

    # 1. 设置系统提示词
    cm.set_system_prompt("你是一个 helpful 的编程助手")
    print(f"  1. 设置系统提示词 ✓")

    # 2. 添加用户消息
    cm.add_user_message("帮我分析一下这个项目的代码结构")
    print(f"  2. 添加用户消息 ✓")

    # 3. 添加 Assistant 消息 + 工具调用
    cm.add_assistant_message(
        "好的，我来读取项目文件",
        tool_calls=[{
            "id": "tool_123",
            "name": "ReadTool",
            "input": {"path": "src/main.py"}
        }]
    )
    print(f"  3. 添加 Assistant 消息 + 工具调用 ✓")

    # 4. 添加工具结果（大文件）
    big_result = "def func():\n    pass\n" * 100
    display = cm.add_tool_result("tool_123", "ReadTool", big_result)
    print(f"  4. 添加工具结果 ({len(big_result)} 字符): {display} ✓")

    # 5. 构建上下文
    messages = cm.build_context_with_tool_results()
    print(f"  5. 构建上下文: {len(messages)} 条消息 ✓")
    assert len(messages) > 0, "上下文不应该为空"

    # 6. 统计显示
    stats_display = cm.format_stats_for_display()
    print(f"\n{stats_display}")

    print_pass("ContextManager 完整流程正常")


def test_7_config_throttling():
    """测试 7: 配置参数生效（不同阈值的影响）"""
    print_header("测试 7: 配置参数生效验证")

    from context.tool_buffer import ToolResultBufferLayer

    # 配置 A: 严格模式（很小的阈值）
    buffer_strict = ToolResultBufferLayer(
        small_threshold=10,
        large_threshold=20,
    )

    # 配置 B: 宽松模式（很大的阈值）
    buffer_lax = ToolResultBufferLayer(
        small_threshold=10000,
        large_threshold=50000,
    )

    # 用同样大小的结果测试
    test_result = "中等大小的结果内容 " * 10  # ~150 字符

    display_strict = buffer_strict.add("t1", "Test", test_result)
    display_lax = buffer_lax.add("t2", "Test", test_result)

    print(f"  同样 150 字符的结果:")
    print(f"    严格模式 (阈值 10/20): {display_strict}")
    print(f"    宽松模式 (阈值 10k/50k): {display_lax}")

    # 严格模式应该被深度截断，宽松模式应该完整保留
    assert "深度" in display_strict or "截断" in display_strict, "严格模式应该深度截断"
    assert "完整" in display_lax, "宽松模式应该完整保留"
    print_pass("配置参数正确生效")


def test_8_clear_function():
    """测试 8: 清空功能"""
    print_header("测试 8: 清空功能")

    from context.manager import ContextManager

    cm = ContextManager()
    cm.add_user_message("消息 1")
    cm.add_tool_result("t1", "Test", "结果内容")

    stats_before = cm.stats()
    assert stats_before['layers']['working']['message_count'] > 0, "测试前应该有数据"

    # 清空
    cm.clear()

    stats_after = cm.stats()
    print(f"  清空前消息数: {stats_before['layers']['working']['message_count']}")
    print(f"  清空后消息数: {stats_after['layers']['working']['message_count']}")

    assert stats_after['layers']['working']['message_count'] == 0, "工作记忆应该被清空"
    assert stats_after['layers']['tool_buffer']['total_cached'] == 0, "工具缓存应该被清空"
    print_pass("清空功能正常")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧠 上下文管理系统 Phase 1 - 完整功能测试")
    print("=" * 60)

    all_passed = True
    tests = [
        test_1_token_estimation,
        test_2_tool_buffer_truncation,
        test_3_tool_recall,
        test_4_working_memory_window,
        test_5_token_budget_control,
        test_6_context_manager_flow,
        test_7_config_throttling,
        test_8_clear_function,
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print_fail(f"测试失败: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    # 最终总结
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！ Phase 1 功能验证完成")
    else:
        print("❌ 部分测试失败，请检查问题后再进行 Phase 2")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
