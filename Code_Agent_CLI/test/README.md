# 测试目录

## 运行测试

```bash
# 在项目根目录执行
uv run python test/test_context_phase1.py
```

## 测试列表

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_context_phase1.py` | 上下文管理系统 Phase 1 完整功能测试 |

## Phase 1 测试覆盖

- ✅ Token 估算（中英文混合、消息列表）
- ✅ ToolResultBuffer 三级截断策略
- ✅ 工具结果完整召回功能
- ✅ WorkingMemory 滑动窗口自动裁剪
- ✅ Token 预算控制（不超上限）
- ✅ ContextManager 完整工作流（添加消息 → 工具结果 → 构建上下文 → 统计）
- ✅ 配置参数生效验证（不同阈值对比）
- ✅ 清空功能

## 添加新测试

1. 新建 `test_xxx.py` 文件
2. 遵循现有测试的风格：
   - 每个测试函数独立
   - 清晰的 print 输出
   - assert 验证
