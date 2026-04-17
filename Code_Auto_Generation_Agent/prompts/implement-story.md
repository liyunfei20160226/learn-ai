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

### 项目结构提示
如果是**前后端分离项目**：
- 后端相关文件，包括依赖文件 → 都放在 `backend/` 目录下
- 前端相关文件，包括依赖文件 → 都放在 `frontend/` 目录下

### 常用技术栈推荐依赖

**对于 React + TypeScript + Vite + Tailwind CSS 项目：**

1. **package.json 推荐包含以下常用依赖：**
```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x"
  },
  "devDependencies": {
    "@eslint/js": "^8.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x",
    "@typescript-eslint/eslint-plugin": "^7.x",
    "@typescript-eslint/parser": "^7.x",
    "@vitejs/plugin-react": "^4.x",
    "autoprefixer": "^10.x",
    "eslint": "^8.x",
    "eslint-plugin-react": "^7.x",
    "eslint-plugin-react-hooks": "^4.x",
    "eslint-plugin-react-refresh": "^0.4.x",
    "globals": "^13.x",
    "postcss": "^8.x",
    "tailwindcss": "^3.x",
    "typescript": "^5.x",
    "vite": "^5.x"
  }
}
```
**必须**把所有这些依赖都写上，这样 `pnpm install` 后 `eslint` 等命令才存在。

2. **必须创建 ESLint 配置文件 `eslint.config.js`**，否则 `pnpm run lint` 会失败。推荐配置：
```js
import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    settings: { react: { version: '18' } },
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      'no-unused-vars': ['warn', { varsIgnorePattern: '^_|^React$' }],
      'react/jsx-no-undef': 'off',  // React 17+ 不需要显式导入 React
      'react/jsx-no-target-blank': 'off',
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
]
```

3. **必须创建 `tsconfig.json` 并开启 JSX 支持**，推荐配置：
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

4. **必须创建** `tsconfig.node.json`、`vite.config.ts`、`tailwind.config.js`、`postcss.config.js` 这些配置文件。

## 项目依赖配置说明

对于Python项目：
- 使用 **标准src-layout结构**推荐：主应用包放在 `src/` 目录下
  ```
  backend/
  ├── pyproject.toml
  ├── src/
  │   └── app/          ← 主应用包在这里
  │       ├── __init__.py
  │       ├── main.py
  │       └── ...
  └── alembic/          ← 迁移脚本/工具目录在这里，不影响打包
  ```
- 使用 `pyproject.toml` 作为项目配置文件
- **所有依赖必须放在 `[project]` section 的 `dependencies` 列表中**
- 如果你需要用到 `mypy`、`pytest`、`ruff` 等开发工具，**也必须把它们添加到 `pyproject.toml` 的依赖列表中**，这样 `uv sync` 才会安装它们
- 如果使用uv包管理器，**不需要单独的 `requirements.txt` 文件**
- 工具配置（ruff、mypy等）也放在 `pyproject.toml` 中

请开始实现。
