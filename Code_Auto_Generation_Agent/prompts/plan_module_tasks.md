## 模块信息

**模块 ID**: {{module_id}}
**模块名称**: {{module_name}}
**模块描述**: {{module_description}}
**代码目录**: {{module_directory}}

### 本模块需要创建的文件

{{files_json}}

## 需要实现的用户故事

{{stories_json}}

---

## 你的任务

请为上述模块规划代码生成任务。使用 add_task 工具添加每个任务。

## ⚠️ 关于任务 ID 格式（简化）

**你不需要纠结 ID 格式！**

- `task_id` 可以用任何唯一标识，如 `T001`, `T002`, `task_1` 等等
- **不需要**手动添加模块前缀（如 `B-MOD-001_01`）
- 系统会自动将所有 ID 统一转换为正确格式
- **依赖项也会自动修正**，你只需要保证同一个模块内依赖关系正确即可

## 要求

1. 每个文件至少对应一个任务
2. 任务描述要包含验收标准详情（从 user story 的 acceptanceCriteria 提取）
3. 按依赖顺序添加任务（先添加被依赖的任务）
4. 添加完所有任务后调用 validate_task_graph 验证
5. 验证通过后调用 finish 标记完成

## 示例

```
add_task(
    task_id="T001",
    title="创建配置文件基础结构",
    description="创建 app/config.py 文件，定义配置类基础结构",
    task_type="backend",
    dependencies=[]
)
```
