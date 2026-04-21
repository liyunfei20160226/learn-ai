# 代码自动生成 - 实现用户故事

## 项目描述

{{PROJECT_DESCRIPTION}}

## 当前要实现的用户故事

**{{STORY_ID}}: {{STORY_TITLE}}**

{{STORY_DESCRIPTION}}

## 验收标准

{{ACCEPTANCE_CRITERIA}}

{{PROJECT_TREE}}

{{LESSONS_LEARNED}}

{{DEPENDENCY_CODE}}

{{ENV_INFO}}

## 你的任务

请实现上述用户故事。遵循以下要求：

1. **遵循架构文档**：严格遵循架构文档中指定的技术栈、依赖版本、目录结构和命名规范
2. **只修改必要文件**：不要修改与当前故事无关的代码
3. **保证可运行**：实现完成后代码应该能够正常运行
4. **满足验收标准**：所有验收标准都必须满足
5. **保持简洁**：不要添加不必要的功能或复杂的抽象
6. **不引入新依赖**：除非绝对必要，否则不要添加架构文档中没有的新依赖

当前工作目录就是项目目录，所有文件操作都相对于这个目录。

## 📌 输出格式要求 - 必须严格遵守！

你必须使用以下markdown代码块格式输出**每个需要创建或修改的文件**：

✅ 正确示例（第一行就是路径，不加语言标记）：
```backend/app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

```frontend/src/App.tsx
import React from 'react';

function App() {
  return <div>Hello World</div>;
}

export default App;
```

❌ 错误示例（加了语言标记，会导致解析失败）：
```python
backend/app/main.py
...
```

⚠️ 严格规则（不遵守会导致解析失败）：
1. **代码块的第一行必须是完整的文件相对路径** ❗️
2. **绝对不要添加任何语言标记**（如 python、tsx、json 等） ❗️
3. 路径后面直接跟内容，不要有空行
4. 每个文件单独一个代码块

不符合格式的输出将被拒绝并重试！

### 项目结构提示
如果是**前后端分离项目**：
- 后端相关文件，包括依赖文件 → 都放在 `backend/` 目录下
- 前端相关文件，包括依赖文件 → 都放在 `frontend/` 目录下

## 重要提醒

⚠️ **必须严格遵循架构文档**：
- 依赖版本以架构文档中的 `dependencies` 为准
- ESLint 配置格式必须与架构文档中指定的 ESLint 版本匹配
- 目录结构必须遵循架构文档中的 `directoryStructure`
- 数据模型必须遵循架构文档中的定义

请开始实现。
