# CCS 前端

基于 Next.js 15 的前端工程。

## 技术栈

- [Next.js 15](https://nextjs.org) - React 框架
- TypeScript - 类型安全
- Tailwind CSS - CSS 框架
- ESLint - 代码检查

## 开发

首先启动开发服务器：

```bash
npm run dev
```

在浏览器中打开 [http://localhost:3000](http://localhost:3000) 查看结果。

你可以开始编辑页面，修改 `app/page.tsx`，页面会自动更新。

## 项目结构

```
frontend/
├── src/
│   └── app/             # App Router 路由
├── public/              # 静态资源
├── next.config.ts       # Next.js 配置
├── tailwind.config.ts   # Tailwind 配置
├── tsconfig.json        # TypeScript 配置
└── package.json
```

## 构建

```bash
npm run build      # 生产构建
npm start          # 启动生产服务
npm run lint       # 代码检查
```

## 后端 API

前端开发时，API 请求会代理到后端 `http://localhost:8000`。需要同时启动后端服务。
