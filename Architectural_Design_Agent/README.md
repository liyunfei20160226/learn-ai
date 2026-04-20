# Architectural Design Agent

自动从 PRD JSON 生成详细的架构设计文档（architecture.json），供后续 Code_Auto_Generation_Agent 生成高质量代码。

## 工作流程

```
Requirements_Analysis_Agent → Architectural_Design_Agent → Code_Auto_Generation_Agent
```

- **输入**: `prd.json`（来自 Requirements_Analysis_Agent）
- **输出**: `architecture.json`（详细架构设计文档）
- **目的**: 在代码生成之前做好整体架构设计，提高代码质量，减少 token 浪费

## 安装

```bash
uv sync
```

## 使用

```bash
# 基本用法
uv run python auto_design.py path/to/prd.json

# 指定输出目录
uv run python auto_design.py path/to/prd.json --output-dir output/myproject

# 指定AI工具
uv run python auto_design.py path/to/prd.json --tool openai

# 覆盖重试次数
uv run python auto_design.py path/to/prd.json --retries 3

# 干跑模式（只打印计划，不实际调用AI）
uv run python auto_design.py path/to/prd.json --dry-run
```

## 配置

复制 `.env.example` 为 `.env` 并修改配置：

```env
DEFAULT_TOOL=claude
CLAUDE_CMD=claude
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
MAX_RETRIES=2
MAX_VALIDATION_ATTEMPTS=1
OUTPUT_BASE_DIR=./output
```

## 输出格式 architecture.json

输出JSON包含以下主要部分：

- `project` - 项目基本信息
- `architecture` - 整体架构概述和技术栈
- `backend` - 后端模块、数据模型、API端点、依赖
- `frontend` - 前端模块、路由、API客户端、依赖
- `implementationOrder` - 实现顺序，与PRD用户故事关联
- `considerations` - 安全、性能、可扩展性考虑

完整schema请参见计划文档。

## 示例

`examples/` 目录包含示例输入输出：
- `prd.json` - 示例PRD输入（待办事项系统）
- `architecture.json` - 生成的架构设计输出
