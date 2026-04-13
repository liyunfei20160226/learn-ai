---
name: ralph
description: "将 PRD 转换为 prd.json 格式供 Ralph 自主代理系统使用。当你已有 PRD，需要转换为 Ralph 的 JSON 格式时使用。触发关键词：convert this prd, turn this into ralph format, create prd.json from this, ralph json"
user-invocable: true
---

# Ralph PRD 转换器

将现有的 PRD 转换为 Ralph 自主执行所用的 prd.json 格式。

---

## 工作内容

接收一个 PRD（markdown 文件或文本），将其转换为 ralph 目录下的 `prd.json`。

---

## 输出格式

```json
{
  "project": "[项目名称]",
  "branchName": "ralph/[功能名称-kebab-case]",
  "description": "[来自 PRD 标题/介绍的功能描述]",
  "userStories": [
    {
      "id": "US-001",
      "title": "[故事标题]",
      "description": "作为一个[用户]，我想要[功能]，以便[收益]",
      "acceptanceCriteria": [
        "标准 1",
        "标准 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## 故事大小：第一重要规则

**每个故事必须能在 ONE（一个）Ralph 迭代中完成（一个上下文窗口内）。**

Ralph 每次迭代都会启动一个全新的 Amp 实例，没有之前工作的记忆。如果故事太大，LLM 在完成前会耗尽上下文，产生破碎的代码。

### 大小合适的故事：
- 添加数据库列和迁移
- 在现有页面添加 UI 组件
- 使用新逻辑更新服务端操作
- 为列表添加筛选下拉框

### 太大了（需要拆分）：
- "构建整个仪表盘" → 拆分为：schema、查询、UI 组件、筛选器
- "添加认证" → 拆分为：schema、中间件、登录 UI、会话处理
- "重构 API" → 每个端点或模式拆分为一个故事

**经验法则：** 如果你不能用 2-3 句话描述变更，那就太大了。

---

## 故事排序：依赖优先

故事按优先级顺序执行。前面的故事不能依赖后面的故事。

**正确顺序：**
1. Schema/数据库变更（迁移）
2. 服务端操作 / 后端逻辑
3. 使用后端的 UI 组件
4. 聚合数据的仪表盘/摘要视图

**错误顺序：**
1. UI 组件（依赖尚不存在的 schema）
2. Schema 变更

---

## 验收标准：必须可验证

每个标准必须是 Ralph 能够 CHECK（检查）的，而不是模糊的描述。

### 好的验收标准（可验证）：
- "在 tasks 表添加 `status` 列，默认值为 'pending'"
- "筛选下拉框选项：全部、进行中、已完成"
- "点击删除会显示确认对话框"
- "类型检查通过"
- "测试通过"

### 坏的验收标准（模糊）：
- "正常工作"
- "用户可以轻松做 X"
- "良好的 UX"
- "处理边缘情况"

### 始终在最后添加这条标准：
```
"Typecheck passes"
```

对于可测试逻辑的故事，还需要添加：
```
"Tests pass"
```

### 对于修改 UI 的故事，还需要添加：
```
"Verify in browser using dev-browser skill"
```

前端故事在获得视觉验证之前不算完成。Ralph 将使用 dev-browser 技能导航到页面，与 UI 交互，并确认更改正常工作。

---

## 转换规则

1. **每个用户故事成为一个 JSON 条目**
2. **ID：** 顺序编号（US-001、US-002 等）
3. **优先级：** 基于依赖顺序，然后是文档顺序
4. **所有故事：** `passes: false` 且 `notes` 为空
5. **branchName：** 从功能名称派生，使用 kebab-case，前缀 `ralph/`
6. **始终添加：** "Typecheck passes" 到每个故事的验收标准

---

## 拆分大型 PRD

如果 PRD 包含大功能，需要拆分它们：

**原文：**
> "添加用户通知系统"

**拆分为：**
1. US-001：在数据库添加 notifications 表
2. US-002：创建发送通知的通知服务
3. US-003：在头部添加通知铃铛图标
4. US-004：创建通知下拉面板
5. US-005：添加标记为已读功能
6. US-006：添加通知偏好设置页面

每个故事都是一个可以独立完成和验证的专注变更。

---

## 示例

**输入 PRD：**
```markdown
# 任务状态功能

添加标记不同任务状态的能力。

## 需求
- 在任务列表上在 pending/in-progress/done 之间切换
- 按状态筛选列表
- 在每个任务上显示状态徽章
- 在数据库中持久化状态
```

**输出 prd.json：**
```json
{
  "project": "TaskApp",
  "branchName": "ralph/task-status",
  "description": "任务状态功能 - 跟踪带有状态指示器的任务进度",
  "userStories": [
    {
      "id": "US-001",
      "title": "在 tasks 表添加状态字段",
      "description": "作为开发者，我需要在数据库中存储任务状态。",
      "acceptanceCriteria": [
        "添加状态列: 'pending' | 'in_progress' | 'done'（默认 'pending'）",
        "成功生成并运行迁移",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "在任务卡片上显示状态徽章",
      "description": "作为用户，我希望一眼就能看到任务状态。",
      "acceptanceCriteria": [
        "每个任务卡片显示彩色状态徽章",
        "徽章颜色: 灰色=pending, 蓝色=in_progress, 绿色=done",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-003",
      "title": "在任务列表行添加状态切换器",
      "description": "作为用户，我希望直接从列表更改任务状态。",
      "acceptanceCriteria": [
        "每行都有状态下拉框或切换器",
        "更改状态立即保存",
        "无需刷新页面即可更新 UI",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 3,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-004",
      "title": "按状态筛选任务",
      "description": "作为用户，我希望筛选列表只查看特定状态的任务。",
      "acceptanceCriteria": [
        "筛选下拉框: 全部 | 待处理 | 进行中 | 已完成",
        "筛选状态持久化在 URL 参数中",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 4,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## 归档之前的运行

**在写入新的 prd.json 之前，如果已有来自不同功能的 prd.json，请检查：**

1. 读取当前的 `prd.json`（如果存在）
2. 检查 `branchName` 是否与新功能的分支名称不同
3. 如果不同且 `progress.txt` 除了表头还有内容：
   - 创建归档文件夹：`archive/YYYY-MM-DD-feature-name/`
   - 将当前 `prd.json` 和 `progress.txt` 复制到归档
   - 重置 `progress.txt` 为新的表头

**运行 ralph.sh 脚本时会自动处理**，但如果你在两次运行之间手动更新 prd.json，请先归档。

---

## 保存前检查清单

写入 prd.json 之前，验证：

- [ ] **之前的运行已归档**（如果 prd.json 存在且 branchName 不同，先归档）
- [ ] 每个故事都能在一次迭代中完成（足够小）
- [ ] 故事按依赖顺序排序（schema → 后端 → UI）
- [ ] 每个故事都有 "Typecheck passes" 作为标准
- [ ] UI 故事都有 "Verify in browser using dev-browser skill" 作为标准
- [ ] 验收标准可验证（不模糊）
- [ ] 没有故事依赖后面的故事
