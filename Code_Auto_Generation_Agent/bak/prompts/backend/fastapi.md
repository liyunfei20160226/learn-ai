你是一个 Python FastAPI 项目专家。项目已经通过 `uv init` 初始化完成，请根据架构文档进行微调。

=== 当前状态 ===

项目已经初始化完成，包含：
- pyproject.toml（uv 标准格式）
- .venv/ 虚拟环境（如果存在）
- app/ 目录已创建

=== 你的任务 ===

## 重要提醒（必须遵守）

1. **必须为"必须创建的文件清单"中列出的**每一个文件**生成完整代码块
2. 不要遗漏任何文件，每个文件都必须单独输出
3. 文件路径必须与架构文档完全一致（例如：`backend/app/main.py`）

根据架构文档进行以下调整：

1. **依赖版本调整**: 严格按照架构文档中的依赖版本更新 `pyproject.toml`
   - FastAPI 版本
   - uvicorn 版本
   - 其他依赖版本
   - 开发依赖：ruff, pytest, mypy

2. **完整配置 pyproject.toml**:
   - [tool.ruff] 完整 lint 配置
   - [tool.pytest.ini_options] 测试配置
   - [tool.mypy] 类型检查配置
   - 确保 `packages = ["app"]` 配置正确
   - **重要**: requires-python 设置为 `">=3.10"`（兼容更多环境）
   - **重要**: 不要创建 .python-version 文件（避免版本锁定问题）

3. **创建项目目录结构**: 严格按照架构文档的 directoryStructure
   - app/main.py FastAPI 入口
   - CORS 中间件配置
   - /health 健康检查路由
   - API 路由挂载
   - 核心配置、数据模型、服务层目录

4. **环境文件**:
   - .env.example 示例配置
   - .gitignore Python 标准

=== 重要提醒 ===

- 不要从零创建项目，只在现有基础上修改和补充
- 依赖版本必须与架构文档完全一致
- 目录结构必须与架构文档完全一致
- 只写骨架，不实现具体业务逻辑
- 生成后项目必须可以直接运行 `uv sync` 和 `uv run uvicorn app.main:app --reload`

=== 架构设计文档 ===

{backend_arch_info}

=== 输出格式 ===

使用代码块格式输出**每个文件**的完整内容，格式如下：

```backend/pyproject.toml
[build-system]
requires = ["hatchling"]
...
```

```backend/app/models/task.py
from pydantic import BaseModel
...
```

## 输出文件检查清单

在生成完成前，请确认你已经为以下所有文件生成了代码：

- `backend/pyproject.toml`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/core/logger.py`
- `backend/app/models/__init__.py`
- `backend/app/models/task.py`
- `backend/app/services/__init__.py`
- `backend/app/services/csv_storage.py`
- `backend/app/api/__init__.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/api/routes/tasks.py`
- `backend/tests/__init__.py`
- `backend/tests/test_main.py`
- `backend/tests/test_models/test_task.py`
- `backend/tests/test_models/__init__.py`
- `backend/tests/test_services/test_csv_storage.py`
- `backend/tests/test_services/__init__.py`
- `backend/tests/test_api/test_tasks.py`
- `backend/tests/test_api/__init__.py`
- `backend/.env.example`
- `backend/.gitignore`

## 重要：路径要求

- 所有代码块的路径都必须以 `backend/` 开头
- 不要使用 `app/` 开头的路径
- 正确示例：```backend/app/main.py
- 错误示例：```app/app/main.py 或 ```app/main.py

**必须确保以上所有文件都有对应的代码块输出，不能缺少任何一个！**
