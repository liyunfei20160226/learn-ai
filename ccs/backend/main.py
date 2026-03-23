"""
CCS Backend - FastAPI 主入口
CCS 邮政销售票据受理系统
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.small_box import router as small_box_router
from app.api.acceptance import router as acceptance_router
from app.api.process import router as process_router
from app.api.status import router as status_router

# 创建 FastAPI 应用
app = FastAPI(
    title="CCS API",
    description="CCS 邮政销售票据受理系统 API",
    version="1.0.0",
)

# CORS 配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(small_box_router)
app.include_router(acceptance_router)
app.include_router(process_router)
app.include_router(status_router)

# 根路径
@app.get("/")
def read_root():
    return {
        "message": "Welcome to CCS API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
