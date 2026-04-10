# Claude Demo - 项目集合

FastAPI + 原生 HTML/CSS/JavaScript 构建的小型 Web 项目集合，采用玻璃拟态设计风格。

## 项目结构

```
claude-demo/
├── main.py                 # FastAPI 后端入口
├── static/                 # 前端静态文件
│   ├── index.html          # 首页 - 分类导航
│   ├── home.css            # 首页样式
│   ├── category.html       # 分类页面
│   ├── category.css        # 分类页面样式
│   ├── todo.*              # 待办清单应用
│   ├── snake.*             # 贪吃蛇游戏
│   ├── sudoku.*            # 数独游戏
│   └── minesweeper.*       # 扫雷游戏
├── pyproject.toml
└── uv.lock
```

## 导航结构

```
首页 (/)
├── ⚙️ 效率工具类
│   └── 待办清单
└── 🎮 游戏类
    ├── 贪吃蛇
    ├── 数独
    └── 扫雷
```

## 启动项目

使用 uv 包管理：

```bash
# 安装依赖
uv sync

# 开发模式启动（自动重载），使用 7777 端口
uv run uvicorn main:app --host 0.0.0.0 --port 7777 --reload
```

然后访问：http://localhost:7777

## 设计风格

所有项目统一使用玻璃拟态（Glassmorphism）设计风格：
- 渐变背景
- 半透明卡片
- 背景模糊效果
- 柔和阴影
- 圆角边框

## 技术栈

- 后端：FastAPI (Python)
- 前端：原生 HTML/CSS/JavaScript
- 包管理：uv
