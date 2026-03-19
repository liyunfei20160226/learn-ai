# CCS MCP Server

MCP 服务器，用于读取 CCS 项目的设计书文档，提取表格数据和 UI 图片，执行数据库操作，供 Claude 端到端生成全栈代码使用。

## 功能

提供以下工具：

### 设计书读取工具
| 工具名 | 功能 | 只读 |
|--------|------|------|
| `ccs_list_design_files` | 列出设计书目录下所有 Excel 设计文件 | ✅ |
| `ccs_read_design_sheet` | 读取指定设计文件中特定工作表的全部表格数据 | ✅ |
| `ccs_extract_images` | 从设计文件提取所有嵌入的 UI 图片保存为 PNG，返回图片路径 | ⚠️ (写文件) |
| `ccs_get_design_info` | 获取设计文件信息（工作表列表、文件大小） | ✅ |
| `ccs_get_output_paths` | 获取输出目录绝对路径 | ✅ |

### 数据库操作工具
| 工具名 | 功能 | 只读 |
|--------|------|------|
| `ccs_execute` | 执行 SQL 语句（CREATE TABLE, DROP TABLE, ALTER TABLE 等） | ❌ (写数据库) |
| `ccs_list_tables` | 列出数据库中所有用户创建的表 | ✅ |
| `ccs_describe_table` | 获取表结构详细信息（列名、类型、约束等） | ✅ |

## 工作流程（配合 `ccs-generate` Skill）

```
1. 用户一句话触发 → "根据xxx设计书，生成解析文档，前后端代码，数据表..."
2. ccs-generate Skill 自动执行以下步骤：
   - 列出可用文件 → ccs_list_design_files
   - 获取文件信息 → ccs_get_design_info
   - 读取各个工作表 → ccs_read_design_sheet
   - 提取 UI 图片 → ccs_extract_images
   - 生成中文解析文档 → 保存到 output
   - 分析数据库设计 → 日文→英文命名转换
   - 创建数据表 → ccs_execute (CREATE TABLE)
   - 验证表结构 → ccs_describe_table
   - 生成后端代码 → model/schema/service/router
   - 生成前端代码 → types/api/page
   - 生成测试代码 → 100% 覆盖率
```

## 角色分工：
- **MCP 服务器**：读取 Excel 提取数据 → 执行 SQL 创建表
- **ccs-generate Skill**：控制整个工作流，指导 Claude 完成代码生成
- **Claude**：理解设计要求，翻译命名，生成前后端代码

## 技术栈

- **Python** + **FastMCP** (MCP Python SDK)
- **uv** - 包管理
- **openpyxl** - Excel 读取和图片提取
- **psycopg2** - PostgreSQL 数据库操作

## 环境配置

可在 `.env` 中配置：
```
# 设计书路径
CCS_DESIGN_DIR=D:/dev/learn-ai/ccs/设计书
CCS_OUTPUT_DIR=D:/dev/learn-ai/ccs/设计书/output

# 数据库连接
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ccs
DB_USER=postgres
DB_PASSWORD=postgres
```

默认已经配置正确。

## 安装依赖

```bash
cd ccs/ccs-mcp
uv sync
```

## 运行

```bash
cd ccs/ccs-mcp
uv run python server.py
```

## 在 Claude Code 中配置

添加到 MCP 配置文件：

```json
{
  "mcpServers": {
    "ccs": {
      "command": "uv",
      "args": ["run", "python", "server.py"],
      "cwd": "D:\\dev\\learn-ai\\ccs\\ccs-mcp"
    }
  }
}
```
