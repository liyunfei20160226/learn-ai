# CCS Backend

CCS 邮政销售票据受理系统 - FastAPI 后端

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── database.py      # 数据库连接配置
│   ├── models.py        # SQLAlchemy 数据模型
│   ├── schemas.py       # Pydantic 数据验证
│   ├── crud.py          # CRUD 操作
│   └── api/            # API 路由
│       ├── __init__.py
│       ├── small_box.py # 小箱相关接口
│       ├── acceptance.py # 受理数据接口
│       ├── process.py   # 工序管理接口
│       └── status.py    # 箱子状态接口
└── main.py             # 主入口
```

## 数据库

数据库: PostgreSQL `ccs`

已创建的表：
- `small_box_info` - 小箱信息表
- `acceptance_data` - 受理数据表
- `process_management` - 工序管理数据表
- `small_box_relation` - 小箱关联表
- `box_status` - 箱子状态表

## 启动服务

```bash
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动后访问: http://localhost:8000/docs

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/small-box/{small_box_no}` | GET | 获取小箱信息 |
| `/api/small-box/` | GET | 小箱列表 |
| `/api/small-box/` | POST | 创建小箱 |
| `/api/small-box/{small_box_no}` | PUT | 更新小箱 |
| `/api/small-box/{small_box_no}` | DELETE | 删除小箱 |
| `/api/small-box/{small_box_no}/status` | GET | 获取小箱状态 |
| `/api/small-box/{small_box_no}/acceptance` | GET | 获取小箱受理数据 |
| `/api/small-box/{small_box_no}/process` | GET | 获取小箱工序数据 |
| `/api/acceptance/` | GET | 受理数据列表 |
| `/api/acceptance/` | POST | 创建受理数据 |
| `/api/acceptance/batch` | POST | 批量创建受理数据 |
| `/api/process/start` | POST | 开始工序 |
| `/api/process/end` | PUT | 结束工序 |
| `/api/status/{system_div}/{small_box_no}` | GET | 获取箱子状态 |
| `/api/status/` | POST | 创建箱子状态 |
| `/api/status/{system_div}/{small_box_no}` | PUT | 更新箱子状态 |
