## PRD 需求文档

{{prd_content}}

## Architecture 架构文档

{{arch_content}}

请分析上述文档，提取需要规划的模块列表。

**要求：**
1. 只输出 JSON 格式，不要其他内容
2. 从架构文档的 backend/frontend/database/shared/infrastructure 中提取
3. 只包含实际存在的模块

**输出格式：**
```json
{
  "modules": [
    {"name": "backend", "description": "后端服务"},
    {"name": "frontend", "description": "前端应用"},
    {"name": "database", "description": "数据库设计"},
    {"name": "shared", "description": "共享资源"},
    {"name": "infrastructure", "description": "基础设施"}
  ]
}
```
