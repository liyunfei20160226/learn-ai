# AutoPRD - 全自动PRD生成Agent

从一句话需求开始，自动通过多轮自问自答完善需求分析，最终生成一份完整规范的产品需求文档。

## 简介

AutoPRD 是基于 Ralph 项目思想扩展的自动化需求分析Agent：

- **输入**：一句简单的项目需求描述
- **过程**：AI自动分析缺失信息 → 提出问题 → AI根据行业最佳实践自问自答 → 多轮迭代完善
- **输出**：完整Markdown格式PRD + 可直接给Ralph使用的 `prd.json`
- **特色**：支持断点续传，达到最大迭代次数后可以接着上次结果继续完善

## 快速开始

首先安装依赖（使用 uv）：

```bash
uv sync
```

配置 OpenAI API：

在项目根目录创建 `.env` 文件（参考 `.env.example`）：
```env
# 必需：你的API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 可选：API地址，默认是 https://api.openai.com/v1
# 可以配置为Azure OpenAI、OneAPI、硅基流动等兼容OpenAI格式的接口
OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：模型名称，默认 gpt-4o
OPENAI_MODEL=gpt-4o
```

运行：

```bash
# ==== 基本用法 ====

# 全自动模式（默认），使用 openai 工具
uv run python autoprd.py "你的一句话需求描述" --tool openai

# 交互式模式，每个问题可以选择让AI回答或自己回答
uv run python autoprd.py "你的一句话需求描述" --tool openai --mode interactive

# 使用本地 claude 命令行工具
uv run python autoprd.py "你的一句话需求描述" --tool claude

# ==== 使用示例 ====

# 示例：一个简单的在线贪吃蛇游戏
uv run python autoprd.py "一个简单的在线贪吃蛇游戏" --tool openai

# 示例：一个待办事项应用，支持拖拽排序
uv run python autoprd.py "一个待办事项应用，支持拖拽排序" --tool openai

# ==== 常用参数组合 ====

# 指定更大的最大迭代次数
uv run python autoprd.py "一个复杂的电商网站" --tool openai --max-iterations 15

# 自定义输出目录
uv run python autoprd.py "我的新项目" --tool openai --output-dir output/my-project

# 交互式模式 + 更多迭代次数
uv run python autoprd.py "企业内部OA系统" --tool openai --mode interactive --max-iterations 20

# ==== 断点续传 ====

# 接着上次结果继续，增加迭代次数
uv run python autoprd.py "在线流程图编辑器" --tool openai --max-iterations 20 --output-dir output/online-flowchart-editor

# ==== 硅基流动 / OneAPI / Azure OpenAI 等自定义端点 ====

# 在 .env 中配置好 OPENAI_BASE_URL 后直接用
uv run python autoprd.py "一个博客系统" --tool openai
```

## 命令行选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--max-iterations N` | 最大迭代次数 | 10（可通过 `.env` 中 `MAX_ITERATIONS` 配置默认值） |
| `--output-dir PATH` | 输出目录 | `output/[功能名称-kebabCase]` |
| `--tool claude\|amp\|openai` | 使用的AI工具：<br>- `claude`/`amp`: 使用本地命令行工具<br>- `openai`: 直接调用OpenAI兼容API | claude |
| `--mode auto\|interactive` | 运行模式：<br>- `auto`: 全自动，AI自动回答所有问题<br>- `interactive`: 交互式，你可以选择每个问题是用AI回答还是自己回答 | auto |

## 输出结构

```
output/
└── your-feature-name/
    ├── prd.md                  # 最终完整PRD（中文）
    ├── prd.json                # Ralph格式JSON，可直接给ralph.sh使用
    └── iteration_history.md   # 完整迭代问答历史（包含每一轮的分析和更新）
```

**文件说明：**
- `prd.md` - **最终需求文档**，只保留最新完整版本，开发直接看这个
- `prd.json` - Ralph 格式，可直接用于自动化开发
- `iteration_history.md` - **完整迭代历史**，记录每一轮AI分析提问和PRD更新，方便追溯

## PRD输出格式

生成的PRD遵循标准结构：

1. **产品概述** - 简短描述项目和要解决的问题
2. **项目目标** - 具体可衡量的目标
3. **用户故事** - 每个故事包含标题、描述、验收标准
4. **功能需求** - 编号列出具体功能
5. **非目标（不在范围内）** - 明确界定本次范围边界
6. **设计考虑** - UI/UX需求
7. **技术考虑** - 已知约束、依赖、性能要求
8. **成功指标** - 如何衡量成功
9. **开放问题** - 仍需澄清的问题（如有）

## 自动回答策略

AutoPRD遵循以下原则自动回答问题：

1. **合理性原则** - 选择该场景下最常见、最合理的选项
2. **最小范围原则** - 如果范围不明确，选择MVP（最小可行产品）范围
3. **保守原则** - 技术决策选择行业主流成熟方案，不选前沿冷门技术
4. **明确性原则** - 答案必须明确，不模糊
5. **文档化原则** - 决策理由写入PRD，便于后续审查

## 断点续传机制

| 场景 | 处理方式 |
|------|----------|
| 首次运行 | 从头开始，生成初始PRD |
| 输出目录已存在且有 `prd.md` | 从现有PRD继续迭代，不重新生成 |
| 达到最大迭代次数 | 输出当前结果，停止循环 |
| 重新运行增加迭代次数 | 接着上次结果继续，节省token |

## 全链路自动化

AutoPRD + Ralph 可以实现从需求到产品的全链路自动化：

```
一句话需求 → AutoPRD自动生成完整PRD → 输出prd.json → Ralph自动开发 → 可运行产品
```

整个过程从需求到产品，完全由AI自动完成，人工只需要等待结果。

## 项目结构

```
Requirements_Analysis_Agent/
├── autoprd.py               # Python 主程序
├── pyproject.toml           # uv 项目配置
├── .python-version          # Python 版本
├── .env.example             # OpenAI 配置示例
├── README.md                # 本文档
├── skills/
│   └── autoprd/
│       └── SKILL.md         # Claude Code Skill定义
├── prompts/
│   ├── autoprd-system.md     # 系统提示词（初始生成）
│   ├── autoprd-analysis.md   # PRD完整性分析提示词
│   ├── autoprd-integration.md # 整合回答到PRD提示词
│   └── autoprd-conversion.md # 转换为Ralph prd.json提示词
├── output/                  # 输出目录（生成的PRD存放在这里）
└── logs/                    # 日志目录
```

## OpenAI API 配置（使用 --tool openai 时）

AutoPRD 支持直接调用 OpenAI 兼容接口，配置方式：

### 方式一：通过 .env 文件（推荐）

在项目根目录创建 `.env` 文件：
```env
# 必需：你的API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 可选：API地址，默认是 https://api.openai.com/v1
# 可以配置为Azure OpenAI、OneAPI、硅基流动等兼容接口地址
OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：模型名称，默认 gpt-4o
OPENAI_MODEL=gpt-4o

# 可选：请求超时时间（秒），默认 300
# OPENAI_TIMEOUT=300

# 可选：失败重试次数，默认 3（网络超时会自动重试）
# OPENAI_MAX_RETRIES=3

# 可选：默认最大迭代次数，默认 10（可通过命令行 --max-iterations 覆盖）
# MAX_ITERATIONS=10
```

### 方式二：通过环境变量

```bash
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o
export OPENAI_TIMEOUT=300
export OPENAI_MAX_RETRIES=3
export MAX_ITERATIONS=10
```

## 依赖

- Python >= 3.8
- uv 包管理器
- 依赖会自动安装：`requests`, `python-dotenv`, `langchain-core`, `langchain-openai`
- 使用 `claude`/`amp` 工具：需要 Claude Code 或 Amp 命令行工具可用
- 使用 `openai` 工具：只需要配置 `OPENAI_API_KEY`

## 许可证

继承自原 Ralph 项目。
