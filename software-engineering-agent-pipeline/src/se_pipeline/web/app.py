"""
FastAPI Application for SE Pipeline Web Interface
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI

from se_pipeline.web.routes import projects, documents, workflow
from se_pipeline.web.workflow_manager import WorkflowManager
from se_pipeline.web.templates import templates

# 初始化 LLM - 文本LLM用于文本总结和分析
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    max_tokens=262144,
    extra_body={
        "enable_thinking": False
    }
)

# 初始化 Vision LLM - 多模态LLM用于图片文字提取，如果没配置单独的就用文本LLM
if os.getenv("VISION_OPENAI_MODEL"):
    vision_llm = ChatOpenAI(
        model=os.getenv("VISION_OPENAI_MODEL"),
        temperature=0.0,
        api_key=os.getenv("VISION_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
        base_url=os.getenv("VISION_OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL")),
        max_tokens=262144,
    )
else:
    vision_llm = llm

# 初始化工作流管理器
workflow_manager = WorkflowManager(llm, vision_llm)

# 创建 FastAPI app
app = FastAPI(
    title="SE Pipeline Web Interface",
    description="Software Engineering Multi-Agent Pipeline - Web Interface",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.get("/")(projects.root)
app.get("/projects")(projects.list_projects)
app.post("/projects")(projects.create_project)
app.get("/projects/{project_id}")(projects.get_project_detail)
app.delete("/projects/{project_id}")(projects.delete_project)
app.post("/projects/{project_id}/delete")(projects.delete_project_post)
app.post("/projects/{project_id}/upload")(documents.upload_file)
app.delete("/projects/{project_id}/documents/{filename}")(documents.delete_document)
app.post("/projects/{project_id}/start")(workflow.start_workflow)
app.post("/projects/{project_id}/answer")(workflow.submit_answers)
app.get("/projects/{project_id}/stream")(workflow.stream_workflow)
app.get("/projects/{project_id}/requirements")(workflow.get_requirements)
app.get("/projects/{project_id}/requirements/download")(workflow.download_requirements)
app.get("/health")(lambda: {"status": "ok"})

# 让模板能访问 node_name_map
templates.env.globals["node_name_map"] = {
    # 主阶段
    "requirements": "需求分析",
    "architecture": "架构设计",
    "ui_prototype": "UI原型",
    "database": "数据库设计",
    "task_breakdown": "任务分解",
    "codegen": "代码生成",
    "codereview": "代码评审",
    "testing": "测试验证",
    "pre_release": "发布前检查",
    "deployment": "部署上线",
    # 需求分析内部节点
    "analyst": "需求分析师",
    "wait_user": "等待用户回答",
    "verifier": "需求验证官",
    "final": "需求生成",
    "quality_gate": "质量闸门",
    "__end__": "结束",
}

# 处理请求验证错误，打印日志方便调试
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"\n[DEBUG] 请求验证失败: {exc}")
    print(f"[DEBUG] 请求URL: {request.url}")
    print(f"[DEBUG] 请求方法: {request.method}")
    body = await request.body()
    print(f"[DEBUG] 请求体: {body.decode('utf-8')}")
    return HTMLResponse(
        "请求参数验证失败，请检查输入格式",
        status_code=422
    )
