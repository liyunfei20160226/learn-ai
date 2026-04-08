"""
Workflow execution routes with SSE streaming
"""
import os
import json
import asyncio
from typing import AsyncGenerator
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from langchain_openai import ChatOpenAI
from se_pipeline.web.workflow_manager import WorkflowManager
from se_pipeline.web.templates import templates


# workflow_manager is already initialized in app, but re-initializing here causes circular import
# So we get it from app after import, but actually we need to initialize here OR get it properly
# Actually easier: just initialize it again here (LLM can be singleton)
# 文本LLM用于文本总结，Vision LLM用于图片提取，支持分开配置
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.0,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    extra_body={
        "enable_thinking": False
    }
)
# 如果配置了单独的Vision LLM，使用单独的，否则复用文本LLM
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

router = APIRouter()


@router.post("/projects/{project_id}/start")
async def start_workflow(request: Request, project_id: str):
    """启动/恢复工作流"""
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
    return templates.TemplateResponse(request, "components/progress_stream.html", {
        "current_node": "analyst" if not state.requirements_verification_passed else "verifier"
    })


@router.get("/projects/{project_id}/stream")
async def stream_workflow(request: Request, project_id: str, from_node: str):
    """SSE 流式输出工作流进度"""
    state = workflow_manager.load_state(project_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        current_node = from_node
        local_state = state

        yield {
            "data": json.dumps({
                "event": "start",
                "data": {"from_node": from_node}
            })
        }
        await asyncio.sleep(0.1)

        while current_node != "__end__":
            # 发送节点开始事件
            node_name = workflow_manager.get_node_name(current_node)
            yield {
                "data": json.dumps({
                    "event": "node_start",
                    "data": {"node": current_node, "name": node_name}
                })
            }
            await asyncio.sleep(0.1)

            if current_node == "document_preprocessor":
                # 文档预处理：使用队列传递进度事件
                # 使用threading.Queue，因为回调来自工作线程
                import queue
                import threading
                progress_queue = queue.Queue()

                def progress_callback(current_file: str):
                    # 同步回调，放入队列
                    progress_queue.put(current_file)

                # 在后台运行处理，不阻塞
                result = None
                next_node = None
                error = None

                def worker():
                    nonlocal result, next_node, error
                    try:
                        result, next_node = workflow_manager.run_step_with_progress(
                            local_state, current_node, progress_callback
                        )
                    except Exception as e:
                        error = e

                thread = threading.Thread(target=worker)
                thread.start()

                # 从队列取出进度并发送
                # 即使没有进度，也要定期发送空消息保活，防止HTTP超时断开
                while thread.is_alive() or not progress_queue.empty():
                    try:
                        current_file = progress_queue.get(timeout=0.5)
                        yield {
                            "data": json.dumps({
                                "event": "document_progress",
                                "data": {"current_file": current_file}
                            })
                        }
                    except queue.Empty:
                        # 空消息保活，不影响前端
                        yield {
                            "data": json.dumps({
                                "event": "keepalive",
                                "data": {}
                            })
                        }
                    await asyncio.sleep(0.5)

                # 等待线程完成
                thread.join()

                # 处理 worker 中抛出的异常
                if error is not None:
                    # 抛出异常让上层处理
                    raise error

                local_state = result
                current_node = next_node
            else:
                # 普通节点，阻塞运行，但是要定期发保活防止断开
                # 启动后台线程运行，主线程发保活
                import threading
                result = None
                next_node = None
                error = None

                def worker():
                    nonlocal result, next_node, error
                    try:
                        result, next_node = workflow_manager.run_step(local_state, current_node)
                    except Exception as e:
                        error = e

                thread = threading.Thread(target=worker)
                thread.start()

                # 定期发保活
                while thread.is_alive():
                    yield {
                        "data": json.dumps({
                            "event": "keepalive",
                            "data": {}
                        })
                    }
                    await asyncio.sleep(0.5)

                # 等待线程完成
                thread.join()

                # 处理异常
                if error is not None:
                    raise error

                local_state = result
                current_node = next_node

            yield {
                "data": json.dumps({
                    "event": "node_complete",
                    "data": {"next_node": current_node}
                })
            }
            await asyncio.sleep(0.1)

            if current_node == "wait_user":
                break

        # 完成
        unanswered = workflow_manager.get_unanswered_questions(local_state)
        yield {
            "data": json.dumps({
                "event": "complete",
                "data": {
                    "done": current_node == "__end__",
                    "has_questions": len(unanswered) > 0,
                    "question_count": len(unanswered)
                }
            })
        }
        # 保存最终状态
        workflow_manager.save_state(project_id, local_state)

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

    return templates.TemplateResponse(request, "components/requirements_view.html", {
        "spec": spec,
        "markdown_content": html_content,
        "project_id": project_id
    })


@router.get("/projects/{project_id}/requirements/download")
async def download_requirements(request: Request, project_id: str):
    """下载需求规格 Markdown 文件"""
    from fastapi.responses import FileResponse
    from se_pipeline.storage.project_store import ProjectStore
    store = ProjectStore()
    project_dir = store.get_project_dir(project_id)
    md_path = project_dir / "01-requirements-spec.md"

    if not md_path.exists():
        return HTMLResponse(
            """<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                    <p class="text-yellow-800">需求规格尚未生成，请完成分析流程</p>
                  </div>""",
            status_code=404
        )

    filename = f"{project_id}-requirements.md"
    return FileResponse(
        str(md_path),
        media_type='text/markdown',
        filename=filename,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
