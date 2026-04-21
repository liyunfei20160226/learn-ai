你是一个 Next.js 项目专家。项目已经通过 `create-next-app` 官方脚手架初始化完成，请根据架构文档进行微调。

=== 当前状态 ===

项目已经通过官方脚手架初始化，包含：
- TypeScript + Tailwind CSS + ESLint
- App Router 结构
- next.config.ts 配置
- tsconfig.json 配置
- tailwind.config.ts 配置
- postcss.config.js 配置
- .gitignore
- package.json

=== 你的任务 ===

根据架构文档进行以下调整：

1. **依赖版本调整**: 严格按照架构文档中的依赖版本更新 `package.json`
   - Next.js 版本
   - React 版本
   - ESLint 版本（**极其重要**，决定配置文件格式）
     - ⚠️ **重要警告**：如果项目已存在 `eslint.config.mjs` 配置文件，说明是 ESLint 9.x 格式
     - ⚠️ **不要降级 ESLint 到 8.x**，否则会导致配置文件格式不兼容！
     - ⚠️ 保持 ESLint 9.x 版本与配置文件格式匹配
   - TypeScript 版本
   - 其他依赖版本

2. **ESLint 配置格式（根据版本）**:
   - **先检查项目中已存在的配置文件**：
     - 如果存在 `eslint.config.mjs` 或 `eslint.config.js`，这是 Next.js 默认创建的 flat config 格式 → **必须修改此文件**
     - 如果存在 `.eslintrc.js` 或 `.eslintrc.json` → 修改此文件
   - ESLint 8.x: 使用 `.eslintrc.js` (CommonJS 格式)
   - ESLint 9.x: 使用 `eslint.config.js` (flat config)
   - **必须根据实际存在的文件和版本选择正确格式**
   - **关键：Next.js 新版本默认创建 `eslint.config.mjs`，这是你应该修改的文件**
   - **必须忽略 `.next` 构建目录**：ESLint 配置中必须添加 ignores: ['.next/']，否则会检查自动生成的构建文件导致错误

3. **完善项目目录结构**: 严格按照架构文档的 directoryStructure
   - 按指定结构创建目录（components/, lib/, types/ 等）
   - 创建数据模型类型定义
   - 创建 API 客户端基础封装
   - 创建工具函数文件

4. **项目微调**:
   - 完善 app/layout.tsx 元数据
   - 完善 globals.css 基础样式
   - app/page.tsx 首页骨架
   - .env.example 环境变量示例

=== 重要提醒 ===

- 不要从零创建项目，只在现有基础上修改和补充
- 依赖版本必须与架构文档完全一致
- ESLint 配置文件格式必须与版本匹配
- 目录结构必须与架构文档完全一致
- 只写骨架，不实现具体业务逻辑
- 生成后项目必须可以直接运行 `npm install` 和 `npm run dev`

=== 架构设计文档 ===

{frontend_arch_info}

=== 输出格式 ===

使用代码块格式输出每个文件的完整内容，格式如下：

```frontend/package.json
{
  "name": "frontend",
  "version": "0.1.0",
...
}
```

```frontend/app/types/task.ts
export interface Task {
...
}
```
