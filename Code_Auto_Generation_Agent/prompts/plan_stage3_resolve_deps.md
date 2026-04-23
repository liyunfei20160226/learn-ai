## 所有模块的任务列表

{{all_tasks_json}}

## PRD 需求文档

{{prd_content}}

## Architecture 架构文档

{{arch_content}}

请整理跨模块依赖关系，并统一任务编号。

**要求：**
1. 统一任务 ID 格式：T001, T002, T003...（全局编号）
2. 修正跨模块依赖：frontend 任务应该依赖 backend API 任务
3. 保持任务顺序合理性：基础模块先，上层模块后
4. 只输出 JSON 格式的任务列表，不要其他内容

**输出格式：**
```json
{
  "tasks": [
    {
      "id": "T001",
      "title": "任务标题",
      "description": "任务描述",
      "type": "backend",
      "dependencies": []
    }
  ]
}
```
