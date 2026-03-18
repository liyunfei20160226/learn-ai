# CCS MCP Server

MCP 服务器，用于读取 CCS 项目的设计书文档，提取表格数据和 UI 图片，供 Claude 生成代码使用。

## 功能

提供以下工具：

| 工具名 | 功能 | 只读 |
|--------|------|------|
| `ccs_list_design_files` | 列出设计书目录下所有 Excel 设计文件 | ✅ |
| `ccs_read_design_sheet` | 读取指定设计文件中特定工作表的全部表格数据 | ✅ |
| `ccs_extract_images` | 从设计文件提取所有嵌入的 UI 图片保存为 PNG，返回图片路径 | ⚠️ (写文件) |
| `ccs_get_design_info` | 获取设计文件信息（工作表列表、文件大小） | ✅ |
| `ccs_get_output_paths` | 获取输出目录绝对路径 | ✅ |

## 工作流程

```
1. 列出可用文件 → ccs_list_design_files
2. 获取文件信息 → ccs_get_design_info
3. 读取各个工作表 → ccs_read_design_sheet
4. 提取 UI 图片 → ccs_extract_images
5. Claude 理解设计要求，生成 DB/前端/后端代码
```

## 角色分工：
- **MCP 服务器**：只负责读取 Excel，提取数据和图片，提供给 Claude
- **Claude**：理解设计要求，设计数据库，生成前后端代码

## 技术栈

- **Python** + **FastMCP** (MCP Python SDK)
- **uv** - 包管理
- **openpyxl** - Excel 读取和图片提取

## 环境配置

可在 `.env` 中配置：
```
CCS_DESIGN_DIR=D:/dev/learn-ai/ccs/设计书
CCS_OUTPUT_DIR=D:/dev/learn-ai/ccs/设计书/output
```

默认已经配置正确。

## 运行

```bash
cd ccs/ccs-mcp
uv sync
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
