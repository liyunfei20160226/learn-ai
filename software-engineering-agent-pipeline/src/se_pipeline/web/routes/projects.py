"""
Project CRUD routes
"""
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from se_pipeline.web.models.requests import CreateProjectRequest
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.web.templates import templates

router = APIRouter()
store = ProjectStore()


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 列出所有项目"""
    project_ids = store.list_projects()
    projects = []
    for project_id in project_ids:
        state = store.load_state(project_id)
        if state is not None:
            projects.append(state)
    return templates.TemplateResponse(request, "index.html", {
        "projects": projects
    })


@router.get("/projects", response_class=HTMLResponse)
async def list_projects(request: Request):
    """列出所有项目片段"""
    project_ids = store.list_projects()
    projects = []
    for project_id in project_ids:
        state = store.load_state(project_id)
        if state is not None:
            projects.append(state)
    return templates.TemplateResponse(request, "components/project_list.html", {
        "projects": projects
    }, headers={"HX-Trigger": "newProjectLoaded"})


@router.post("/projects")
async def create_project(request: Request, form_data: CreateProjectRequest):
    """创建新项目"""
    print(f"\n[DEBUG] 收到创建项目请求: project_id={form_data.project_id}, project_name={form_data.project_name}")
    # 检查是否已存在
    existing = store.load_state(form_data.project_id)
    if existing is not None:
        print("[DEBUG] 创建失败: 项目已存在")
        return HTMLResponse(
            f"""项目 ID {form_data.project_id} 已存在，请使用其他 ID""",
            status_code=409
        )

    # 创建初始状态
    state = PipelineState(
        project_id=form_data.project_id,
        project_name=form_data.project_name,
        current_stage="requirements",
        original_user_requirement=form_data.original_requirement,
    )
    store.save_state(form_data.project_id, state)
    print(f"[DEBUG] 创建成功: project_id={form_data.project_id}")
    # 前端会处理跳转
    return HTMLResponse("ok", status_code=200)


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

    return templates.TemplateResponse(request, "project_detail.html", {
        "state": state,
        "unanswered": unanswered,
        "node_name_map": node_name_map
    })


@router.delete("/projects/{project_id}")
async def delete_project(request: Request, project_id: str):
    """删除项目"""
    store.delete_project(project_id)
    project_ids = store.list_projects()
    projects = []
    for pid in project_ids:
        state = store.load_state(pid)
        if state is not None:
            projects.append(state)
    return templates.TemplateResponse(request, "components/project_list.html", {
        "projects": projects
    })


@router.post("/projects/{project_id}/delete")
async def delete_project_post(request: Request, project_id: str):
    """删除项目 (POST 版本，兼容某些环境)"""
    print(f"\n[DEBUG] 收到删除请求: project_id={project_id}")
    print(f"[DEBUG] 请求方法={request.method}, 路径={request.url}")
    store.delete_project(project_id)
    project_ids = store.list_projects()
    projects = []
    for pid in project_ids:
        state = store.load_state(pid)
        if state is not None:
            projects.append(state)
    print(f"[DEBUG] 删除完成，剩余 {len(projects)} 个项目")
    return templates.TemplateResponse(request, "components/project_list.html", {
        "projects": projects
    })


@router.post("/projects/{project_id}/change-request")
async def submit_change_request(request: Request, project_id: str):
    """提交需求变更文字，添加到问答历史，触发新一轮分析"""
    form_data = await request.form()
    change_text = form_data.get("change_text", "")

    if not change_text:
        return HTMLResponse("空内容", status_code=400)

    from se_pipeline.web.workflow_manager import WorkflowManager
    from langchain_openai import ChatOpenAI
    import os
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    if os.getenv("VISION_OPENAI_MODEL"):
        vision_llm = ChatOpenAI(
            model=os.getenv("VISION_OPENAI_MODEL"),
            temperature=0.0,
            api_key=os.getenv("VISION_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
            base_url=os.getenv("VISION_OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL")),
        )
    else:
        vision_llm = llm
    workflow_manager = WorkflowManager(llm, vision_llm)

    state = workflow_manager.load_state(project_id)
    if state is None:
        return HTMLResponse("项目不存在", status_code=404)

    # 将变更信息作为用户回答添加到问答历史
    state.requirements_qa_history.append({
        "question": "[系统] 需求变更补充说明",
        "answer": change_text
    })

    # 重置状态，触发新一轮分析
    state = state.model_copy(update={
        "needs_more_questions": True,
        "requirements_verification_passed": False,
        "entered_verification": False,
    })
    state.update_timestamp()

    workflow_manager.save_state(project_id, state)

    # 保存成功后，直接返回进度流式页面，和点击开始分析一致
    from se_pipeline.web.workflow_manager import node_name_map
    return templates.TemplateResponse(request, "components/progress_stream.html", {
        "project_id": project_id,
        "current_node": "analyst",
        "node_name_map": node_name_map
    })
