## PRD 需求文档

{{prd_content}}

## Architecture 架构文档

{{arch_content}}

## 当前模块

**模块名：{{module_name}}**
**模块描述：{{module_desc}}**

请为上述模块规划代码生成任务。

**要求：**
1. 只规划当前模块的任务，不要涉及其他模块
2. 任务 ID 格式：{{module_prefix}}_001, {{module_prefix}}_002...
3. 任务类型：backend, frontend, database, shared, infrastructure
4. 依赖只能引用当前模块内的任务

**使用 add_task 工具添加每个任务，使用 validate_task_graph 验证，最后调用 finish。**
