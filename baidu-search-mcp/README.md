# 百度搜索 MCP Server

百度搜索 MCP 服务器 - **适合国内网络环境**，让 Claude Code 能够联网搜索获取最新信息。

## 特点

- ✅ **无需 API Key** - 直接使用，免费搜索
- ✅ **适合国内网络** - 访问百度，速度快
- ✅ **标准 MCP 协议** - 兼容 Claude Code
- ✅ **返回结构化结果** - 标题、链接、摘要都有

## 安装

```bash
cd baidu-search-mcp
npm install
npm run build
```

## Claude Code 配置

在你的 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "baidu-search": {
      "command": "node",
      "args": ["D:\\dev\\learn-ai\\baidu-search-mcp\\dist\\index.js"]
    }
  }
}
```

**注意 Windows 路径**: 需要用双反斜杠 `\\` 或者正斜杠 `/`

## 使用方法

配置完成后重启 Claude Code，就可以使用了：

```
帮我搜索一下 今天最新的科技新闻
```

```
搜索一下 Next.js 15 有什么新特性
```

## 工具说明

### `baidu_search`
使用百度搜索引擎搜索网页。

**参数**:
- `query` (必填): 搜索关键词
- `limit` (可选): 返回结果数量，默认 10，范围 1-20

## 许可

MIT
