# CCS Frontend - 邮政销售票据受理系统前端

基于 Next.js 15 + TypeScript + Tailwind CSS 开发。

## 开发

```bash
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000) 访问。

## 构建

```bash
npm run build
npm start
```

## 代理配置

`next.config.ts` 中已配置代理将 `/api/*` 请求转发到后端 `http://localhost:8000/api/*`。
