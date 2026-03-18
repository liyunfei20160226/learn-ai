# CCS 项目

基于 Next.js + FastAPI + PostgreSQL 的全栈项目。

## 项目结构

```
ccs/
├── 设计书/            # 功能详细设计文档（包含日文原版Excel界面定义书）
├── ccs_mcp/          # MCP 服务器 - PostgreSQL 数据库访问
├── frontend/          # Next.js 15 前端工程 (TypeScript + Tailwind CSS)
├── backend/           # FastAPI 后端工程 (Python + uv 包管理)
└── README.md          # 项目说明
```

## 技术栈

- **前端**: Next.js 15 + TypeScript + Tailwind CSS
- **后端**: FastAPI + SQLAlchemy + uv (包管理)
- **MCP 服务器**: FastMCP + MCP Protocol - 提供 AI 数据库访问能力
  - `ccs_list_tables` - 列出所有表
  - `ccs_describe_table` - 查看表结构
  - `ccs_query` - 只读查询
  - `ccs_execute` - 写操作
  - `ccs_get_schema_info` - Schema 概览
- **数据库**: PostgreSQL 18

## 设计文档

- `设计书/` - 日文原版 Excel 格式功能详细设计文档

## 数据库信息

- 主机: `localhost:5432`
- 数据库名: `ccs`
- 用户名: `postgres`
- 密码: `postgres`

## 快速开始

### 启动后端

```bash
cd backend
uv sync                          # 安装依赖
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档: http://localhost:8000/docs

### 启动前端

```bash
cd frontend
npm run dev
```

前端地址: http://localhost:3000

## 开发说明

- 后端使用 **uv** 作为包管理工具，不使用 pip + requirements.txt
- 所有依赖定义在 `backend/pyproject.toml`，锁定版本在 `uv.lock`
- 前端使用 npm 管理依赖
