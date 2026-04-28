# 🧠 Code Agent - 基于 LLM 的智能编程助手

一个可扩展、支持多模型的命令行 AI 编程助手，类似 Claude Code 的开源实现。

---

## 📋 项目概述

Code Agent 是一个**思考-行动循环**架构的 AI 编程助手。你可以用自然语言描述需求，它会自动调用工具来完成任务：

- 📖 **读取文件** - 理解现有代码
- ✏️ **写入文件** - 创建或修改代码
- 🔍 **搜索文件** - grep 查找关键字
- 📂 **列出目录** - 浏览项目结构
- 🚀 **执行命令** - 运行脚本、编译、测试
- 🔌 **MCP 工具** - 支持标准 MCP Servers，无限扩展
- 📦 **Skill 系统** - 可插拔操作手册，扩展 Agent 能力

### ✨ 核心特性

| 特性 | 状态 | 说明 |
|------|------|------|
| **可插拔 LLM** | ✅ | 支持 Claude、OpenAI、Ollama（本地模型） |
| **MCP 协议支持** | ✅ | 兼容 Model Context Protocol，无限扩展工具能力 |
| **Skill 系统** | ✅ | 可插拔操作手册，让 Agent 学会新技能 |
| **分层上下文管理** | ✅ | Token 预算可控，大文件自动截断 |
| **彩色终端体验** | ✅ | 6 种主题可选，支持实时预览 |
| **工具调用动画** | ✅ | 旋转加载动画，显示执行耗时 |
| **配置持久化** | ✅ | 主题、偏好自动保存 |

---

## 🏗️ 整体架构

> 💡 下图使用 Mermaid 绘制，GitHub、VS Code 等均支持直接渲染。

```mermaid
flowchart TD
    %% 用户层
    User["👤 用户<br/>自然语言输入"]
    
    %% REPL 层
    User --> REPL
    
    subgraph REPL ["REPL 循环 - main.py"]
        direction LR
        R1["1. 读取用户输入"] --> R2["2. 传递给 Agent"]
        R2 --> R3["3. 输出结果"]
        R3 --> R4["4. 循环"]
        R4 --> R1
    end
    
    %% Agent 层
    REPL --> Agent
    
    subgraph Agent ["Agent 核心 - agent/core.py"]
        direction TB
        Think["🧠 思考<br/>调用 LLM"] --> Decision{"决定调用工具?"}
        Decision -->|NO| Answer["返回答案"]
        Decision -->|YES| Execute["执行工具<br/>ToolRegistry"]
        Execute -->|工具结果| Buffer["ToolResultBuffer<br/>自动分级截断"]
        Buffer --> Think
    end
    
    %% 基础设施层
    Agent --> CM["ContextManager<br/>分层上下文管理"]
    Agent --> LLM["LLM Provider<br/>多模型适配器"]
    Agent --> TR["Tool Registry<br/>工具注册中心"]
    
    %% ContextManager 子层
    CM --> WM["Working Memory<br/>最近对话滑动窗口"]
    CM --> TB["ToolBuffer<br/>工具结果分级截断"]
    
    %% LLM Provider 子层
    LLM --> Claude["Claude API"]
    LLM --> OpenAI["OpenAI 兼容"]
    LLM --> Ollama["Ollama 本地"]
    
    %% Tool 子层
    TR --> Bash["Bash 命令执行"]
    TR --> MCP["MCP Tools<br/>（filesystem/github/...）"]
    TR --> Skill["Skill 工具<br/>操作手册"]
    
    %% MCP 子系统
    subgraph MCP_System ["MCP 子系统 - mcp_client/"]
        direction TB
        M1["MCPClient<br/>管理单个 Server"]
        M2["MCPManager<br/>全局管理器"]
        M3["MCPTool<br/>工具适配器"]
    end
    
    TR --> MCP_System
    
    %% Skill 子系统
    subgraph Skill_System ["Skill 系统 - skills/"]
        direction TB
        S1["Skill Registry<br/>技能注册中心"]
        S2["Skill Creator<br/>创建新技能"]
    end
    
    TR --> Skill_System
    
    %% 样式定义
    classDef user fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef repl fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef agent fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef infra fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef layer fill:#fafafa,stroke:#616161,stroke-width:1px
    classDef mcp fill:#e3f2fd,stroke:#1565c0,stroke-width:1px
    classDef skill fill:#fce4ec,stroke:#880e4f,stroke-width:1px
    
    %% 应用样式
    class User user
    class R1,R2,R3,R4 repl
    class Think,Decision,Answer,Execute,Buffer agent
    class CM,LLM,TR infra
    class WM,TB,Claude,OpenAI,Ollama,Bash,MCP,Skill layer
    class REPL repl
    class Agent agent
    class CM,LLM,TR infra
    class MCP_System mcp
    class Skill_System skill
```

### 📦 主要模块说明

| 模块 | 目录 | 职责 |
|------|------|------|
| **Agent 核心** | `src/agent/` | 思考-行动循环，协调 LLM 和工具 |
| **上下文管理** | `src/context/` | 分层 Token 管理，工具结果分级截断 |
| **LLM Provider** | `src/llm/` | 统一的多模型适配器接口 |
| **工具系统** | `src/tools/` | 可插拔工具注册与执行 |
| **MCP 客户端** | `src/mcp_client/` | Model Context Protocol 客户端，管理外部 MCP Servers |
| **Skill 系统** | `skills/` | 可插拔操作手册，扩展 Agent 能力 |
| **终端输出** | `src/utils/console.py` | 彩色输出、主题、动画 |
| **提示词** | `src/prompts/` | System Prompt 等提示词模板 |

---

## 🔌 MCP (Model Context Protocol)

**MCP 是标准化的工具调用协议**，它让我们可以复用整个社区的工具实现，而不是每一个都自己写。

### 内置支持

项目已内置 **Filesystem MCP Server**，提供 14 个专业文件操作工具：

| 工具 | 说明 |
|------|------|
| `read_file` | 读取文件完整内容 |
| `read_text_file` | 读取文本文件（带编码检测） |
| `read_media_file` | 读取图片/音频文件 |
| `read_multiple_files` | 批量读取多个文件 |
| `write_file` | 创建或覆盖文件 |
| `edit_file` | 基于行的文件编辑 |
| `create_directory` | 创建目录 |
| `list_directory` | 列出目录内容 |
| `list_directory_with_sizes` | 列目录并显示大小 |
| `directory_tree` | 递归目录树视图 |
| `move_file` | 移动/重命名文件 |
| `search_files` | 递归搜索文件 |
| `get_file_info` | 获取文件元数据 |
| `list_allowed_directories` | 列出允许访问的目录 |

### 添加更多 MCP Servers

只需在 `.env` 中添加配置，自动加载：

```ini
# Filesystem（默认已配置）
MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."

# GitHub（示例）
MCP_SERVER_GITHUB="npx @modelcontextprotocol/server-github --token YOUR_TOKEN"

# Brave Search（示例）
MCP_SERVER_BRAVE="npx @modelcontextprotocol/server-brave-search --api-key YOUR_KEY"
```

---

### 📂 Filesystem MCP Server 详细说明

这是最常用的 MCP Server，提供专业的文件操作能力，替代了旧的本地文件工具。

#### 前置条件

1. **安装 Node.js**（必需）
   - 下载地址：https://nodejs.org/
   - 推荐版本：Node.js 18+
   - 验证安装：
     ```bash
     node --version   # 检查 node
     npx --version    # 检查 npx
     ```

#### 运行方式

**方式 1：自动运行（推荐）** ✨

只需在 `.env` 中配置好，启动 Code Agent 时会自动运行：

```ini
MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."
```

- 第一个参数：允许访问的根目录（`.` 表示当前目录，可以设为绝对路径）
- 首次运行时 `npx` 会自动从 npm 下载包，后续使用缓存

**方式 2：手动预安装（离线可用）**

如果网络环境不好，或者想完全离线运行，可以预先全局安装：

```bash
# 1. 全局安装 MCP filesystem server
npm install -g @modelcontextprotocol/server-filesystem

# 2. 验证安装
which server-filesystem   # Mac/Linux
where server-filesystem   # Windows

# 3. 修改 .env 配置（直接调用命令，不经过 npx）
MCP_SERVER_FILESYSTEM="server-filesystem ."
```

这样启动速度更快，而且完全不需要网络。

#### 验证安装

在 Code Agent 中输入 `/mcps` 命令查看状态：

```
📦 MCP Server 状态
  ✅ filesystem: 已连接
      - read_file: [MCP:filesystem] Read the complete contents...
      - write_file: [MCP:filesystem] Create a new file...
      ...（共 14 个工具）
```

看到 `✅` 表示连接成功！

#### 常见问题排查

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| ❌ filesystem 未连接 | Node.js 未安装 | 安装 Node.js 后重启 |
| ❌ filesystem 未连接 | npx 命令找不到 | 检查 Node.js 是否在 PATH 中 |
| ❌ filesystem 未连接 | 首次运行网络超时 | 手动运行 `npx @modelcontextprotocol/server-filesystem .` 预下载 |
| 工具调用报错 | 目录权限问题 | 检查 MCP 配置的根目录是否有访问权限 |

#### 手动测试 MCP Server

如果不确定 MCP Server 是否正常工作，可以单独测试：

```bash
# 直接运行 MCP Server（看是否有报错）
npx @modelcontextprotocol/server-filesystem .

# 如果启动不报错，按 Ctrl+C 退出即可
```

正常启动后应该静默运行等待输入（没有输出就是好消息），如果有报错信息会显示在终端。

---

## 📦 Skill 系统

**Skill 是给 LLM 看的「操作手册」**，它告诉 Agent 如何正确地完成某一类任务。

### Skill 结构

```
skills/
└── my-skill/
    ├── SKILL.md      # 操作手册（给 LLM 看）
    ├── README.md     # 人类可读说明
    ├── examples/     # 示例代码/配置
    └── config.json   # 元数据
```

### 内置 Skill

- **`skill-creator`** - 帮助你创建新的 Skill

### 使用方式

在对话中，你可以让 Agent 调用 Skill，或者直接通过命令查看：

```bash
/skills     # 列出所有已加载的 Skill
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 uv
uv sync

# 安装 Node.js（用于运行 MCP Servers，可选但推荐）
# 从 https://nodejs.org/ 下载安装
```

### 2. 配置 API Key

```bash
# 复制配置模板
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# 选择 LLM 提供商
LLM_PROVIDER=claude  # 或 openai / ollama

# Claude 配置（推荐，工具调用最稳定）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# OpenAI 兼容配置（支持 DeepSeek、通义千问等）
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o
# OPENAI_BASE_URL=https://api.openai.com/v1

# Ollama 本地模型（无需 API Key）
# OLLAMA_MODEL=qwen2.5:7b

# MCP 配置（已启用 filesystem）
MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."
```

### 3. 运行程序

```bash
uv run python src/main.py
```

**首次启动会提示选择颜色主题，实时预览效果后确认即可。**

### 4. 使用示例

```
👤 你好，帮我看看这个项目的结构
🤖 Agent: 好的，让我先查看一下项目目录...

🔧 调用工具: list_directory
   path: .
   ✅ 工具执行完成

🤖 Agent: 这是一个 Code Agent 项目，主要结构如下：
- src/ 源代码目录
  - agent/ Agent 核心逻辑
  - mcp_client/ MCP 客户端
  - llm/ LLM 提供商适配器
  - tools/ 工具实现
- skills/ Skill 目录
- test/ 测试脚本
- .config/ 用户配置
```

---

## 💻 特殊命令

在对话中可以输入以下命令：

| 命令 | 作用 |
|------|------|
| `/stats` | 显示上下文 Token 使用统计 |
| `/clear` | 清空当前上下文（开始新对话） |
| `/skills` | 列出所有已加载的 Skill |
| `/mcps` | 显示所有 MCP Server 连接状态和可用工具 |
| `/help` | 显示帮助信息 |
| `exit` / `quit` / `退出` | 退出程序 |

---

## ⚙️ 主要配置说明

所有配置项都在 `.env` 文件中：

### 🤖 LLM 相关配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_PROVIDER` | `claude` | LLM 提供商：`claude` / `openai` / `ollama` |
| `MAX_ITERATIONS` | `20` | 单轮最大工具调用次数（防止无限循环） |

#### Claude 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ANTHROPIC_API_KEY` | 必填 | Anthropic API Key |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | 模型名称 |

#### OpenAI 兼容配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | 必填 | API Key |
| `OPENAI_MODEL` | `gpt-4o` | 模型名称 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 地址（可改为兼容服务） |

#### Ollama 本地模型配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OLLAMA_MODEL` | 必填 | 模型名称（如 `qwen2.5:7b`） |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama 服务地址 |

---

### 🔌 MCP 相关配置

所有以 `MCP_SERVER_` 开头的环境变量都会被自动识别为 MCP Server 配置。

格式：
```ini
MCP_SERVER_<名称>="<命令> <参数>"
```

常用 MCP Server 配置示例：

```ini
# Filesystem（文件操作，默认已启用）
MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."

# GitHub（需要 token）
# MCP_SERVER_GITHUB="npx @modelcontextprotocol/server-github --token ghp_..."

# Brave Search
# MCP_SERVER_BRAVE="npx @modelcontextprotocol/server-brave-search --api-key YOUR_KEY"

# Postgres
# MCP_SERVER_POSTGRES="npx @modelcontextprotocol/server-postgres postgresql://user:pass@localhost/db"
```

---

### 🧠 上下文管理配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CONTEXT_TOTAL_BUDGET` | `150000` | 总 Token 预算上限 |
| `CONTEXT_WORKING_WINDOW_SIZE` | `10` | 工作记忆窗口（保留最近 N 轮对话） |
| `CONTEXT_WORKING_MAX_TOKENS` | `50000` | 工作记忆最大 Token 数 |
| `CONTEXT_TOOL_BUFFER_MAX_TOKENS` | `80000` | 工具结果缓冲最大 Token 数 |
| `CONTEXT_TOOL_SMALL_THRESHOLD` | `1000` | 小结果阈值（字符数，以下完整保留） |
| `CONTEXT_TOOL_LARGE_THRESHOLD` | `5000` | 大结果阈值（字符数，以上深度截断） |

**预算分配建议：**

| 模型类型 | `TOTAL_BUDGET` | `TOOL_BUFFER_MAX_TOKENS` |
|---------|----------------|---------------------------|
| Claude 3.5 Sonnet | `200000` | `120000` |
| GPT-4o | `128000` | `80000` |
| 本地 7B 模型 | `32000` | `12000` |

---

## 🧪 运行测试

```bash
# 运行上下文管理 Phase 1 测试
uv run python test/test_context_phase1.py
```

---

## 📁 项目结构

```
Code_Agent_CLI/
├── src/
│   ├── agent/
│   │   └── core.py              # Agent 思考-行动循环核心
│   ├── context/                  # 分层上下文管理
│   │   ├── __init__.py
│   │   ├── base.py             # Layer 抽象基类
│   │   ├── manager.py          # ContextManager 统一门面
│   │   ├── tool_buffer.py      # 工具结果缓冲层（分级截断）
│   │   ├── token_counter.py    # Token 估算工具
│   │   └── working.py          # 工作记忆层（滑动窗口）
│   ├── llm/                      # LLM 提供商适配器
│   │   ├── __init__.py
│   │   ├── base.py             # LLMProvider 抽象基类
│   │   ├── claude_provider.py  # Claude API 适配
│   │   ├── factory.py          # Provider 工厂函数
│   │   ├── ollama_provider.py  # Ollama 本地模型适配
│   │   └── openai_provider.py  # OpenAI 兼容 API 适配
│   ├── mcp_client/               # MCP 客户端
│   │   ├── __init__.py
│   │   ├── client.py           # 单个 MCP Server 客户端
│   │   └── manager.py          # MCP Server 全局管理器
│   ├── prompts/                  # 提示词模板
│   │   └── system.md           # 系统提示词
│   ├── tools/                    # 工具实现
│   │   ├── base.py             # BaseTool 基类
│   │   ├── bash.py             # Bash 命令执行工具
│   │   └── loader.py           # 工具注册与加载
│   ├── utils/                    # 工具函数
│   │   ├── command_handler.py  # REPL 命令处理器
│   │   └── console.py          # 彩色终端输出、主题、动画
│   └── main.py                  # 程序入口、REPL 循环
├── skills/                       # Skill 目录
│   └── skill-creator/           # 创建新 Skill 的 Skill
│       ├── SKILL.md
│       └── README.md
├── test/
│   ├── README.md                # 测试说明
│   └── test_context_phase1.py  # 上下文管理 Phase 1 测试
├── .config/                     # 用户配置（自动生成）
│   └── theme.json             # 主题设置
├── .env                         # 环境配置（自行创建）
├── .env.example                # 配置模板
├── pyproject.toml              # 项目配置、依赖
└── README.md                   # 本文件
```

---

## 🎯 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | REPL 骨架 + 基础工具 | ✅ |
| Phase 1 | 多 LLM Provider 架构 | ✅ |
| Phase 2 | 彩色终端 + 主题系统 | ✅ |
| Phase 3 | 分层上下文管理 | ✅ |
| Phase 4 | **MCP 协议支持（当前）** | ✅ |
| Phase 5 | **Skill 系统（当前）** | ✅ |
| Phase 6 | Planner + Reviewer 两阶段思考 | 🚧 |
| Phase 7 | 工具结果精确对齐 | ⏳ |
| Phase 8 | 历史对话摘要层 | ⏳ |
| Phase 9 | 长期记忆持久化 | ⏳ |

---

## 📝 开发命令

```bash
# 代码检查
uv run ruff check src/

# 自动修复
uv run ruff check src/ --fix

# 运行测试
uv run python test/test_context_phase1.py
```

---

## 🤝 许可证

MIT License
