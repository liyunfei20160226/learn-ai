"""
FastAPI Application for SE Pipeline Web Interface
"""
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI

from se_pipeline.web.routes import projects, documents, workflow
from se_pipeline.web.workflow_manager import WorkflowManager

# 初始化 LLM
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    extra_body={
        "enable_thinking": False
    }
)
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

# 获取当前文件所在目录
import sys
from pathlib import Path
current_dir = Path(__file__).parent

# 模板和静态文件
templates = Jinja2Templates(directory=str(current_dir / "templates"))

# 注册路由
app.get("/")(projects.root)
app.get("/projects")(projects.list_projects)
app.post("/projects")(projects.create_project)
app.get("/projects/{project_id}")(projects.get_project_detail)
app.delete("/projects/{project_id}")(projects.delete_project)
app.post("/projects/{project_id}/upload")(documents.upload_file)
app.delete("/projects/{project_id}/documents/{filename}")(documents.delete_document)
app.post("/projects/{project_id}/start")(workflow.start_workflow)
app.post("/projects/{project_id}/answer")(workflow.submit_answers)
app.get("/projects/{project_id}/stream")(workflow.stream_workflow)
app.get("/projects/{project_id}/requirements")(workflow.get_requirements)
app.get("/health")(lambda: {"status": "ok"})

# 让模板能访问 node_name_map
templates.env.globals["node_name_map"] = {
    "analyst": "需求分析师",
    "wait_user": "等待用户回答",
    "verifier": "需求验证官",
    "final": "需求生成",
    "quality_gate": "质量闸门",
    "__end__": "结束",
}
