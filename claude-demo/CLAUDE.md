# CLAUDE.md

本文档为 Claude Code 在本仓库工作时提供指引。

## 项目概述

这是一个小型 Web 项目集合，使用 **FastAPI (Python 后端)** + **原生 HTML/CSS/JavaScript (前端)** 构建。所有项目共享统一的玻璃拟态设计风格，运行在单个 FastAPI 服务上。

## 包管理器

本项目使用 **uv** 进行包管理。

## 常用命令

### 安装依赖
```bash
uv sync
```

### 添加新依赖
```bash
uv add <包名>
```

### 运行服务器
```bash
uv run python main.py
```
服务器运行在 `http://localhost:8000`

### 开发模式运行（自动重载）
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 架构

### 后端 (Python/FastAPI)
- `main.py` - 单个文件包含所有路由定义
- 所有前端文件都是静态文件，由 FastAPI 托管
- 只使用内存存储（无数据库）
- 路由：
  - `GET /` - 项目主页，展示所有项目链接
  - `GET /todo` - 待办清单应用
  - `GET /snake` - 贪吃蛇游戏
  - `GET /sudoku` - 数独游戏
  - `GET /api/todos` - 待办 API（列表、创建、更新、删除）

### 前端 (`static/` 目录下的静态文件)
- 每个项目有独立的 `.html`、`.css`、`.js` 文件
- 所有前端逻辑使用原生 JavaScript（无框架）
- 设计风格：玻璃拟态（渐变背景、backdrop blur、半透明卡片）
- 文件：
  - `static/index.html` + `home.css` - 项目主页卡片
  - `static/todo.*` - 待办清单应用
  - `static/snake.*` - 贪吃蛇游戏（HTML5 Canvas）
  - `static/sudoku.*` - 数独游戏

### 新增项目设计规范
- 保持一致的玻璃拟态风格，和现有项目统一
- 每个页面底部添加 "← 返回项目主页" 链接
- 更新主页 `static/index.html` 添加新项目卡片
- 在 `main.py` 添加新路由
- 所有 CSS/JS 路径使用绝对路径：`/static/xxx.css`
- 保持简洁 - 小项目优先使用原生 JavaScript

## 现有项目

1. **待办清单** (`/todo`) - 待办管理，支持筛选、增删改、完成状态切换
2. **贪吃蛇** (`/snake`) - 经典贪吃蛇游戏，方向键控制
3. **数独** (`/sudoku`) - 数独益智游戏，三种难度，检查解答，提示功能
