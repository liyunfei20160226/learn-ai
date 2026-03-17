# CCS 后端

基于 FastAPI 的后端服务。

## 技术栈

- [FastAPI](https://fastapi.tiangolo.com/) - Python Web 框架
- SQLAlchemy - ORM
- PostgreSQL - 数据库
- **uv** - 包管理工具（推荐比 pip 更快更可靠）

## 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由
│   │   └── health.py # 健康检查接口
│   └── core/         # 核心配置
│       └── database.py # 数据库连接配置
├── main.py           # 应用入口
├── .env              # 环境变量
├── pyproject.toml    # 项目依赖定义
├── uv.lock           # 锁定的依赖版本
└── README.md
```

## 环境变量

`.env` 文件:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ccs
```

## 开发

### 安装依赖

```bash
uv sync
```

### 启动开发服务器

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或者激活虚拟环境：

```bash
source .venv/Scripts/activate
uvicorn main:app --reload --port 8000
```

### 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

### 添加新依赖

```bash
uv add <package-name>
```

### 删除依赖

```bash
uv remove <package-name>
```

## 可用接口

- `GET /` - 欢迎信息
- `GET /health` - 健康检查（包含数据库连接测试）
- `GET /api/health` - API 健康检查

## 数据库

- 使用 SQLAlchemy ORM
- 模型定义在 `app/models/`
- 数据模式 schemas 定义在 `app/schemas/`
- 业务逻辑 services 在 `app/services/`
