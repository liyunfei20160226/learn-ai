"""
Project CRUD routes
"""
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from se_pipeline.web.models.requests import CreateProjectRequest
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.types.pipeline import PipelineState

current_file = Path(__file__)
templates_dir = current_file.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()
store = ProjectStore()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 列出所有项目"""
    projects = store.list_projects()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": projects
    })


@router.get("/projects", response_class=HTMLResponse)
async def list_projects(request: Request):
    """列出所有项目片段"""
    projects = store.list_projects()
    return templates.TemplateResponse("components/project_card.html", {
        "request": request,
        "projects": projects
    }, headers={"HX-Trigger": "newProjectLoaded"})


@router.post("/projects")
async def create_project(request: Request, form_data: CreateProjectRequest):
    """创建新项目"""
    # 检查是否已存在
    existing = store.load_state(form_data.project_id)
    if existing is not None:
        return HTMLResponse(
            f"""<div class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4" hx-swap-oob="beforeend">#project-list">
                    <p class="text-red-800">项目 ID {form_data.project_id} 已存在，请使用其他 ID</p>
                </div>"""
        )

    # 创建初始状态
    state = PipelineState(
        project_id=form_data.project_id,
        project_name=form_data.project_name,
        current_stage="requirements",
        original_user_requirement=form_data.original_requirement,
    )
    store.save_state(form_data.project_id, state)

    # 重定向到项目详情页
    return HTMLResponse(
        f"""<script>window.location.href = '/projects/{form_data.project_id}';</script>"""
    )


@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def get_project_detail(request: Request, project_id: str):
    """项目详情页"""
    state = store.load_state(project_id)
    if state is None:
        return HTMLResponse(
            """<div class="bg-red-50 border border-red-200 rounded-lg p-8">
                    <h2 class="text-xl font-semibold text-red-800">项目不存在</h2>
                    <p class="text-red-600 mt-2">返回<a href="/" class="underline">首页</a></p>
                  </div>""",
            status_code=404
        )

    from se_pipeline.web.workflow_manager import node_name_map
    # 获取未回答问题
    unanswered = []
    for item in state.requirements_qa_history:
        if item["answer"] is None:
            unanswered.append(item)

    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "state": state,
        "unanswered": unanswered,
        "node_name_map": node_name_map
    })


@router.delete("/projects/{project_id}")
async def delete_project(request: Request, project_id: str):
    """删除项目"""
    store.delete_project(project_id)
    projects = store.list_projects()
    return templates.TemplateResponse("components/project_card.html", {
        "request": request,
        "projects": projects
    })
