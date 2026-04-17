# 项目结构生成完成 - 请给出构建和检查命令

## 项目描述

{{PROJECT_DESCRIPTION}}

## 当前项目目录结构

```
{{PROJECT_TREE}}
```

## 任务

项目基础结构和依赖文件已经生成完成。请你根据项目的语言和架构，告诉我：

1. **安装依赖需要运行哪些命令**？（可以是多个命令，按执行顺序列出）
   - 对于Python项目：**推荐使用uv包管理器**，使用 `uv sync` 安装依赖，如果pyproject.toml在子目录需要 `cd`
   - 对于Node.js项目：根据锁文件选择包管理器，pnpm优先（更快更好）：
     - 存在 `pnpm-lock.yaml` → `pnpm install`
     - 存在 `yarn.lock` → `yarn install`
     - 存在 `package-lock.json` → `npm install`
     - **没有锁文件（第一次安装）** → 默认使用 `pnpm install`（推荐pnpm更快更好）
   - 对于其他语言：使用项目对应的标准包管理器

2. **代码质量检查需要运行哪些命令**？（lint、语法检查等）
   - 对于Python项目：**推荐使用ruff**，命令是 `ruff check . --fix`（--fix 自动修复可修复的代码风格问题）
   - 对于Node.js项目：lint工具（eslint等）是本地安装在项目内，需要通过包管理器执行：
     - 使用pnpm → `pnpm exec eslint .`
     - 使用npm → `npx eslint .`
3. **类型检查需要运行哪些命令**？（如果项目有静态类型检查）
   - 对于TypeScript项目：`pnpm exec tsc --noEmit` 或 `npx tsc --noEmit`
4. **自动化测试需要运行哪些命令**？

## 输出格式要求

请**严格**按以下JSON格式输出，不要输出其他内容：

```json
{
  "install": ["command1", "command2"],
  "quality_check": ["command1", "command2"],
  "type_check": ["command1", "command2"],
  "test": ["command1", "command2"]
}
```

- 如果某个分类不需要命令，给空数组 `[]`
- 所有命令都应该是可以直接在shell中运行的完整命令
- 如果依赖文件或配置文件位于**子目录**中，你需要在命令前加上 `cd 子目录 &&` 切换到正确目录再执行
  - 例如：package.json 在 frontend/ 目录 → `cd ./frontend && npm install`
  - 例如：pyproject.toml 在 backend/ 目录 → `cd ./backend && uv sync`
- 不要添加任何解释，只输出JSON
