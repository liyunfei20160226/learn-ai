# CCS PostgreSQL MCP 服务器

这是一个 **MCP (Model Context Protocol)** 服务器，用于让 AI 助手访问 CCS PostgreSQL 数据库。

## 功能

提供以下工具：

| 工具名 | 功能 | 只读 |
|--------|------|------|
| `ccs_list_tables` | 列出数据库 schema 中的所有表 | ✅ |
| `ccs_describe_table` | 获取表结构详细信息（列、类型、主键、外键） | ✅ |
| `ccs_query` | 执行只读 SELECT 查询 | ✅ |
| `ccs_get_schema_info` | 获取完整 schema 概览信息（包含行数估计） | ✅ |
| `ccs_execute` | 执行写操作（INSERT/UPDATE/DELETE/CREATE/ALTER 等） | ❌ |

## 技术栈

- **Python** + **FastMCP** (官方 MCP Python SDK)
- **uv** - 包管理
- **psycopg2-binary** - PostgreSQL 驱动
- **pydantic** - 输入验证

## 项目结构

```
ccs_mcp/
├── server.py           # 主服务器代码
├── pyproject.toml      # 项目依赖定义
├── uv.lock             # 锁定依赖版本
├── .env                # 环境变量（数据库连接）
└── README.md           # 说明文档
```

## 环境配置

`.env` 文件已经配置好：
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ccs
```

## 运行

### 使用 uv 运行

```bash
cd ccs/ccs_mcp
uv run python server.py
```

### 在 Claude Code 中配置

添加到 Claude Code 的 MCP 配置文件：

```json
{
  "mcpServers": {
    "ccs": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "/d/dev/learn-ai/ccs/ccs_mcp"
    }
  }
}
```

Windows 路径（如果需要）：
```json
{
  "mcpServers": {
    "ccs": {
      "command": "uv",
      "args": ["run", "python", "D:\\dev\\learn-ai\\ccs\\ccs_mcp\\server.py"],
      "cwd": "D:\\dev\\learn-ai\\ccs\\ccs_mcp"
    }
  }
}
```

## 使用示例

### 列出所有表

```
ccs_list_tables(schema_name="public")
```

### 查看表结构

```
ccs_describe_table(table_name="sales_invoice")
```

### 查询数据

```
ccs_query(sql="SELECT * FROM sales_invoice WHERE status = 'pending' LIMIT 10")
```

### 创建表

```
ccs_execute(sql="CREATE TABLE example (id SERIAL PRIMARY KEY, name TEXT);")
```

## 安全说明

- `ccs_query` 只允许 SELECT 查询
- `ccs_execute` 允许任何 SQL 执行，包括 DROP 和 DELETE，请谨慎使用
- 当前配置仅用于本地开发

## 依赖安装

```bash
cd ccs_mcp
uv sync
```
