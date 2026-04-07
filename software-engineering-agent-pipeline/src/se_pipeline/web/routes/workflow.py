"""
Workflow execution routes with SSE streaming
"""
import json
import asyncio
from typing import AsyncGenerator
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
from pathlib import Path
from se_pipeline.web.workflow_manager import WorkflowManager
from se_pipeline.web.models.requests import AnswerQuestionsRequest
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.agents.document_preprocessor import DocumentPreprocessorAgent

current_dir = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(current_dir / "templates"))

router = APIRouter()
from se_pipeline.web.app import workflow_manager


@router.post("/projects/{project_id}/start")
async def start_workflow(request: Request, project_id: str):
    """启动/恢复工作流"""
    state = workflow_manager.load_state(project_id)

    # 如果有文档且未处理，先预处理
    if not state.documents_processed and state.source_documents_dir:
        state = workflow_manager.process_documents(state)

    workflow_manager.save_state(project_id, state)

    return HTMLResponse("<script>window.location.reload()</script>")


@router.post("/projects/{project_id}/answer")
async def submit_answers(request: Request, project_id: str):
    """提交问题答案"""
    form_data = await request.form()
    state = workflow_manager.load_state(project_id)

    # 更新问答历史
    unanswered_count = 0
    for idx, item in enumerate(state.requirements_qa_history):
        if item["answer"] is None:
            unanswered_count += 1
            form_key = f"answer-{unanswered_count}"
            if form_key in form_data:
                item["answer"] = form_data[form_key]

    state.update_timestamp()
    workflow_manager.save_state(project_id, state)

    # 下一步由 SSE 流式处理
    return templates.TemplateResponse("components/progress_stream.html", {
        "request": request,
        "current_node": "analyst" if not state.requirements_verification_passed else "verifier"
    })


@router.get("/projects/{project_id}/stream")
async def stream_workflow(request: Request, project_id: str, from_node: str):
    """SSE 流式输出工作流进度"""
    state = workflow_manager.load_state(project_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        current_node = from_node

        yield {
            "event": "start",
            "data": json.dumps({"from_node": from_node})
        }
        await asyncio.sleep(0.1)

        while current_node != "__end__":
            # 发送节点开始事件
            node_name = workflow_manager.get_node_name(current_node)
            yield {
                "event": "node_start",
                "data": json.dumps({
                    "node": current_node,
                    "name": node_name
                })
            }
            await asyncio.sleep(0.1)

            # 运行节点
            state, current_node = workflow_manager.run_step(state, current_node)

            yield {
                "event": "node_complete",
                "data": json.dumps({"next_node": current_node})
            }
            await asyncio.sleep(0.1)

            if current_node == "wait_user":
                break

        # 完成
        unanswered = workflow_manager.get_unanswered_questions(state)
        yield {
            "event": "complete",
            "data": json.dumps({
                "done": current_node == "__end__",
                "has_questions": len(unanswered) > 0,
                "question_count": len(unanswered)
            })
        }

    return EventSourceResponse(event_generator())


@router.get("/projects/{project_id}/requirements", response_class=HTMLResponse)
async def get_requirements(request: Request, project_id: str):
    """获取最终需求规格 HTML 视图"""
    state = workflow_manager.load_state(project_id)
    if state is None or state.requirements_spec is None:
        return HTMLResponse(
            """<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                    <p class="text-yellow-800">需求规格尚未生成，请完成分析流程</p>
                  </div>"""
        )

    # 转换 Markdown 为 HTML（简单转换，满足需求展示）
    import markdown
    spec = state.requirements_spec
    markdown_text = spec.to_markdown()
    html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])

    return templates.TemplateResponse("components/requirements_view.html", {
        "request": request,
        "spec": spec,
        "markdown_content": html_content,
        "project_id": project_id
    })
