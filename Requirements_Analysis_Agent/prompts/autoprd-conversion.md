# PRD转换为Ralph JSON格式

## 转换规则

### 输出格式要求：
```json
{
  "project": "[项目名称]",
  "branchName": "{branch_name}",
  "description": "[项目描述]",
  "userStories": [
    {
      "id": "US-001",
      "title": "[故事标题]",
      "description": "As a [user], I want [feature] so that [benefit]",
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

## 转换规则：
1. 每个用户故事对应一个JSON条目
2. ID顺序：US-001, US-002, US-003...
3. 优先级：按依赖顺序，1, 2, 3...
4. 所有故事设置 passes: false
5. 每个故事必须添加 "Typecheck passes" 到 acceptanceCriteria
6. 如果故事涉及UI修改，必须添加 "Verify in browser using dev-browser skill"
7. 故事必须足够小，每个故事一个迭代就能完成，过大的请拆分
8. stories按依赖关系排序（schema -> backend -> UI）

## 项目信息：
- 项目名称: {project_name}
- 分支名称: {branch_name}
- 描述: {project_description}

## 输入PRD：

{final_prd}

请只输出合法的JSON，不要有其他内容。
