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

## 你的任务

请实现上述用户故事。遵循以下要求：

1. **遵循现有架构**：参考项目现有的代码风格、命名规范和架构模式
2. **只修改必要文件**：不要修改与当前故事无关的代码
3. **保证可运行**：实现完成后代码应该能够正常运行
4. **满足验收标准**：所有验收标准都必须满足
5. **保持简洁**：不要添加不必要的功能或复杂的抽象

当前工作目录就是项目目录，所有文件操作都相对于这个目录。

## 输出格式要求

你必须使用以下markdown代码块格式输出**每个需要创建或修改的文件**：

```
filepath
file content here
```

示例：
```
backend/app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

```
frontend/src/App.tsx
import React from 'react';

function App() {
  return <div>Hello World</div>;
}

export default App;
```

每个文件一个代码块。第一行必须是**完整的文件相对路径**。不要省略路径。

请开始实现。
