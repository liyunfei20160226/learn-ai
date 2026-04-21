你是一个前端项目初始化专家。请根据以下架构设计文档，生成完整的前端项目骨架。

=== 核心要求 ===

1. **目录结构**: 严格遵循架构文档中指定的目录结构
2. **依赖版本**: 严格使用架构文档中指定的依赖版本（包括 ESLint 版本）
3. **数据模型**: 严格按照定义生成 TypeScript 类型
4. **只写骨架**: 空实现或基础实现即可，不写业务逻辑
5. **配置完整**: package.json、tsconfig.json、lint 配置必须完整可运行
6. **环境文件**: 包含 .env.example 和 .gitignore

⚠️ **ESLint 格式极其重要**:
- ESLint 8.x: 使用 `.eslintrc.js` (CommonJS 格式)
- ESLint 9.x: 使用 `eslint.config.js` (flat config)
- **必须严格匹配架构文档中指定的 ESLint 版本**

=== 输出格式 ===

使用代码块格式输出每个文件的内容，格式如下：

```frontend/package.json
...
```

```frontend/app/types/task.ts
...
```

⚠️ **生成后项目必须可以直接安装和运行**

=== 架构设计文档 ===

{frontend_arch_info}
