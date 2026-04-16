# Auto Coding Agent

全自动代码生成Agent，根据 `prd.json`（由 Requirements_Analysis_Agent 生成）自动调用 AI 逐个实现用户故事，直至完成整个项目开发。

支持两种AI后端：
- **Claude Code CLI**：使用本地 Claude Code 命令行工具（推荐，上下文感知更好）
- **OpenAI API**：直接调用 OpenAI API（兼容各种OpenAI格式API）

## 功能特点

- 全自动循环开发，无需人工干预
- 支持断点续传，随时停止恢复
- 自动质量检查（lint、类型检查、测试）
- 自动修复错误
- Git自动提交
- 模块化架构，易于扩展
- 支持命令行和Web两种界面（开发中）

## 安装

```bash
# 克隆项目后
uv sync
```

## 配置

复制 `.env.example` 到 `.env` 并编辑：

```env
# 默认AI工具：claude 或 openai
# 可以通过命令行 --tool 参数覆盖
DEFAULT_TOOL=claude

# Claude CLI 配置
CLAUDE_CMD=claude

# OpenAI API 配置（使用openai工具时需要）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

## 使用方法

### 命令行

```bash
# 基本用法（自动默认输出到 output/<prd-filename>）
uv run python auto_coding.py path/to/prd.json

# 你也可以显式指定目标目录
uv run python auto_coding.py path/to/prd.json --target-dir path/to/output

# 指定AI工具
uv run python auto_coding.py prd.json --tool openai

# 只处理N个故事（方便测试）
uv run python auto_coding.py prd.json --max-stories 1

# 跳过Git提交
uv run python auto_coding.py prd.json --no-git

# 跳过质量检查
uv run python auto_coding.py prd.json --no-quality-check

# 干运行，只打印计划
uv run python auto_coding.py prd.json --dry-run
```

### 命令行选项

| 选项 | 说明 |
|------|------|
| `prd_path` | prd.json 文件路径（必填） |
| `--target-dir` | 生成代码的目标目录（可选，默认：`output/<prd-filename>`） |
| `--tool <claude\|openai>` | 指定AI工具，覆盖.env配置（与 Requirements_Analysis_Agent 统一） |
| `--max-stories N` | 最多处理N个故事后停止 |
| `--retries N` | 每个故事最大重试次数 |
| `--fix-attempts N` | 修复错误最大尝试次数 |
| `--no-git` | 禁用Git自动提交 |
| `--no-quality-check` | 禁用质量检查 |
| `--resume` | 从现有进度文件恢复 |
| `--dry-run` | 只打印计划，不实际执行 |

## prd.json 格式

```json
{
  "project": "项目名称",
  "branch_name": "功能分支名",
  "description": "项目详细描述",
  "user_stories": [
    {
      "id": "US-001",
      "title": "用户登录功能",
      "description": "作为用户，我想要能够输入用户名密码登录系统",
      "acceptance_criteria": [
        "验证通过后跳转到首页",
        "验证失败显示错误信息",
        "提供记住登录状态选项"
      ],
      "priority": 1,
      "passes": false
    }
  ]
}
```

## 工作流程

```
启动 auto_coding.py
  ↓
1. 加载配置和prd.json
  ↓
2. 检查是否有进度文件（断点续传）
  ↓
3. 主循环：
  ┌─────────────────────────
  │  所有故事完成？→ 结束
  │  选择下一个优先级最高的未完成故事
  │  ↓
  │  构建Prompt（包含项目上下文和经验教训）
  │  ↓
  │  调用AI后端实现故事
  │  ↓
  │  运行质量检查
  │  ↓
  │  检查不通过 → 自动修复（最多N次）→ 仍失败 → 标记失败
  │  ↓
  │  通过 → Git提交 → 标记完成 → 更新进度文件
  │  ↓
  └─────────────────────────
  重复
  ↓
4. 输出完成报告
  ↓
5. 退出
```

## 项目结构

```
├── auto_coding.py          # 命令行入口
├── config.py               # 配置管理
├── pyproject.toml          # 项目依赖配置
├── core/
│   ├── ai_backend.py       # AI后端抽象基类
│   ├── claude_cli.py       # Claude CLI实现
│   ├── openai_api.py       # OpenAI API实现
│   ├── prd_loader.py       # PRD加载解析
│   ├── story_manager.py    # 用户故事状态管理
│   ├── progress_tracker.py # 进度跟踪
│   ├── quality_checker.py  # 质量检查
│   ├── git_manager.py      # Git操作
│   └── generator.py        # 主生成引擎
├── utils/
│   ├── logger.py           # 日志工具
│   ├── subprocess.py       # 子进程封装
│   └── file_utils.py       # 文件操作
├── prompts/                # 提示词模板
├── web/                    # Web UI（开发中）
├── output/                 # 输出目录
└── logs/                   # 日志目录
```

## 全链路工作流

与 Requirements_Analysis_Agent 配合使用，实现从需求到产品的全链路自动化：

```
一句话需求
  ↓
Requirements_Analysis_Agent
  ↓
生成 prd.json
  ↓
Auto Coding Agent
  ↓
全自动编码完成
  ↓
得到可运行项目
```

## License

MIT
