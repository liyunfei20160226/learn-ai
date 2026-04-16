"""
AutoPRD Web UI - FastAPI Application
"""

import sys
import traceback
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.task_manager import task_manager, Task, TaskStatus  # noqa: E402

app = FastAPI(title="AutoPRD Web UI")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates - 使用手动初始化 Jinja2 Environment 避免 Starlette Jinja2Templates 的兼容性问题
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Import autoprd after adding path


@app.get("/")
async def read_root(request: Request):
    template = jinja_env.get_template("index.html.jinja")
    html = template.render({"request": request})
    return HTMLResponse(content=html)


@app.post("/api/start")
async def start_task(
    requirement: str = Form(...),
    tool: str = Form("openai"),
    mode: str = Form("auto"),
    max_iterations: int = Form(10),
    rag_topk: int = Form(5),
    output_name: str = Form(""),
    background_dir: str = Form(""),
):
    """Start a new AutoPRD generation task with optional background directory"""
    # Create task with optional custom output directory name
    task = task_manager.create_task(requirement, output_name)
    task_id = task.task_id

    # Process background directory if provided
    processed_background_dir = None
    if background_dir and background_dir.strip():
        bd = background_dir.strip()
        # Resolve path: absolute path uses directly, relative path relative to project root
        path_obj = Path(bd)
        if path_obj.is_absolute():
            processed_background_dir = str(path_obj)
        else:
            processed_background_dir = str(project_root / bd)
        task_manager.add_log(task_id, f"✓ 背景目录: {processed_background_dir}\n")

    # Import config from .env
    from dotenv import load_dotenv
    if (project_root / ".env").exists():
        load_dotenv(project_root / ".env")

    # Start task in background
    def run_task(task: Task):
        try:
            task_manager.add_log(task.task_id, f"开始生成PRD: {task.requirement}\n")

            # Patch stdout to capture logs
            original_stdout = sys.stdout

            class LogCapturer:
                def __init__(self):
                    # Proxy original attributes needed by stdout
                    self.encoding = original_stdout.encoding

                def write(self, data):
                    if isinstance(data, str):
                        for line in data.splitlines():
                            if line.strip():
                                task_manager.add_log(task.task_id, line)
                    original_stdout.write(data)

                def flush(self):
                    original_stdout.flush()

                def reconfigure(self, **kwargs):
                    original_stdout.reconfigure(**kwargs)

            sys.stdout = LogCapturer()

            try:
                from autoprd import (
                    load_background_documents,
                    build_rag_vectorstore,
                    run_prd_generation,
                )

                # Load env
                if (project_root / ".env").exists():
                    load_dotenv(project_root / ".env")

                # Load background directory if provided
                vectorstore = None
                if processed_background_dir:
                    bg_path = Path(processed_background_dir)
                    if bg_path.exists():
                        documents = load_background_documents(processed_background_dir)
                        if documents:
                            vectorstore = build_rag_vectorstore(documents)
                            task_manager.add_log(task_id, f"\n✓ 共加载背景文档: {len(documents)} 块\n")
                    else:
                        task_manager.add_log(task_id, f"⚠️ 背景目录不存在: {processed_background_dir}\n")

                # Run generation
                run_prd_generation(
                    requirement=requirement,
                    tool=tool,
                    mode=mode,
                    max_iterations=max_iterations,
                    output_dir=Path(task.output_dir),
                    vectorstore=vectorstore,
                    rag_topk=rag_topk,
                    task=task,
                )

                if task.should_stop:
                    task_manager.add_log(task.task_id, "\n⚠️ 任务被用户停止")
                    task_manager.stop_task(task_id)
                else:
                    task_manager.add_log(task.task_id, "\n✅ PRD生成完成！")
                    task_manager.complete_task(task_id)

            except Exception as e:
                error_msg = str(e)
                full_tb = traceback.format_exc()
                task_manager.add_log(task.task_id, f"\n❌ 错误: {error_msg}")
                task_manager.add_log(task.task_id, "\n完整错误详情:")
                for line in full_tb.splitlines():
                    task_manager.add_log(task.task_id, line)
                task_manager.fail_task(task_id, error_msg)
            finally:
                sys.stdout = original_stdout

        except Exception as e:
            error_msg = str(e)
            task_manager.add_log(task.task_id, f"\n❌ 未捕获错误: {error_msg}")
            task_manager.fail_task(task_id, error_msg)

    task_manager.start_task(task_id, run_task)
    task_manager.add_log(task_id, f"任务已创建，ID: {task_id}")
    task_manager.add_log(task_id, f"需求: {requirement}")
    task_manager.add_log(task_id, f"工具: {tool}, 模式: {mode}, 最大迭代: {max_iterations}")
    if background_dir and background_dir.strip():
        task_manager.add_log(task_id, f"背景目录: {processed_background_dir}")

    return {"task_id": task_id, "status": "started"}


@app.get("/api/events/{task_id}")
async def stream_events(request: Request, task_id: str):
    """Server-Sent Events endpoint for real-time log streaming"""
    task = task_manager.get_task(task_id)
    if not task:
        return StreamingResponse(iter(["data: 错误: 任务不存在\n\n"]), media_type="text/event-stream")

    async def event_generator():
        last_index = 0
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Send new logs
            with task_manager._lock:
                logs = task.logs
                if last_index < len(logs):
                    for i in range(last_index, len(logs)):
                        line = logs[i]
                        # Escape newlines in SSE
                        line = line.replace("\n", " ").rstrip()
                        if line:
                            yield f"data: {line}\n\n"
                    last_index = len(logs)

            # Check if task is done or waiting for user answer
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED, TaskStatus.WAITING_FOR_ANSWER]:
                yield f"data: [DONE] {task.status}\n\n"
                break

            import asyncio
            yield ""
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """Get task status"""
    task = task_manager.get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return {
        "task_id": task.task_id,
        "status": task.status,
        "requirement": task.requirement,
        "logs_count": len(task.logs),
        "output_files": task.output_files,
        "error": task.error,
    }




@app.get("/api/download/{task_id}/{filename}")
async def download_file(task_id: str, filename: str):
    """Download generated file"""
    task = task_manager.get_task(task_id)
    if not task or not task.output_dir:
        return {"error": "Task not found"}
    file_path = task.output_dir / filename
    if not file_path.exists():
        return {"error": "File not found"}
    return FileResponse(
        file_path,
        filename=filename,
        media_type="text/plain"
    )


@app.get("/api/questions/{task_id}")
async def get_pending_questions(task_id: str):
    """Get pending questions for interactive mode"""
    task = task_manager.get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return {
        "task_id": task_id,
        "status": task.status,
        "pending_questions": task.pending_questions,
    }


@app.post("/api/answer/{task_id}")
async def submit_user_answers(task_id: str, request: Request):
    """Submit user answers for interactive mode"""
    task = task_manager.get_task(task_id)
    if not task:
        return {"error": "Task not found"}

    # Parse form data manually since FastAPI Form doesn't support List[dict] directly
    form_data = await request.form()
    answers = []
    i = 0
    while True:
        question_key = f"answers[{i}][question]"
        choice_key = f"answers[{i}][choice]"
        answer_key = f"answers[{i}][answer]"
        if question_key not in form_data:
            break
        answers.append({
            "question": form_data[question_key],
            "choice": form_data[choice_key],
            "answer": form_data[answer_key],
        })
        i += 1

    with task_manager._lock:
        task.user_answers = answers
        task.answers_ready = True
        if task.answer_condition:
            task.answer_condition.notify_all()

    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
