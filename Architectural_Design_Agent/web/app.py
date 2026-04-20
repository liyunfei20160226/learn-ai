"""
Architectural Design Agent Web UI - FastAPI Application
"""

import json
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.task_manager import Task, TaskStatus, task_manager  # noqa: E402

app = FastAPI(title="Architectural Design Agent Web UI")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


@app.get("/")
async def read_root(request: Request):
    template = jinja_env.get_template("index.html.jinja")
    html = template.render({"request": request})
    return HTMLResponse(content=html)


@app.post("/api/start")
async def start_task(
    prd_file: UploadFile = File(...),
    tool: str = Form("openai"),
    retries: int = Form(2),
    max_validation_attempts: int = Form(1),
    output_name: str = Form(...),
    dry_run: bool = Form(False),
):
    """Start a new architecture generation task"""
    # Load env from .env first to get default tool
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Read uploaded PRD file
    content = await prd_file.read()
    try:
        prd_data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        return {"error": f"PRD JSON 格式错误: {e}"}, 400

    # Extract project name for display
    prd_name = prd_data.get("project", prd_data.get("project_name", "未知项目"))

    # Create task
    task = task_manager.create_task(prd_name, output_name)
    task_id = task.task_id
    output_dir = Path(task.output_dir)

    # Save PRD to output directory
    prd_file_path = output_dir / "input.prd.json"
    with open(prd_file_path, "w", encoding="utf-8") as f:
        json.dump(prd_data, f, ensure_ascii=False, indent=2)

    # Start task in background
    def run_task(task: Task):
        try:
            import logging

            # Patch stdout to capture print output
            original_stdout = sys.stdout

            class StreamCapturer:
                def __init__(self, original_stream):
                    self.original_stream = original_stream
                    self.encoding = original_stream.encoding

                def write(self, data):
                    if isinstance(data, str):
                        for line in data.splitlines():
                            if line.strip():
                                task_manager.add_log(task.task_id, line)
                    self.original_stream.write(data)

                def flush(self):
                    self.original_stream.flush()

                def reconfigure(self, **kwargs):
                    self.original_stream.reconfigure(**kwargs)

            sys.stdout = StreamCapturer(original_stdout)

            # Add custom handler to capture logger output (most reliable method)
            class TaskLogHandler(logging.Handler):
                def emit(self, record):
                    msg = self.format(record)
                    task_manager.add_log(task.task_id, msg)

            # Get logger and add handler
            from utils.logger import get_logger
            logger = get_logger()
            task_handler = TaskLogHandler()
            task_handler.setFormatter(logger.handlers[0].formatter)  # Use same format as console
            logger.addHandler(task_handler)

            try:
                from config import get_config
                from core.architecture_generator import ArchitectureGenerator
                from core.prd_loader import load_prd

                # Reload env
                if env_path.exists():
                    load_dotenv(env_path)

                config = get_config()

                # Override config with form values
                if tool and tool.strip():
                    config.ai_backend = tool.strip()
                config.max_retries = retries
                config.max_validation_attempts = max_validation_attempts

                # Load PRD
                prd = load_prd(str(prd_file_path))
                if not prd:
                    raise ValueError("加载 PRD 失败")

                # Create generator and run
                # Note: the output_name will be used as filename_prefix
                # The output directory is output/web/<output_name>
                generator = ArchitectureGenerator(
                    config=config,
                    prd=prd,
                    output_dir=str(output_dir),
                    prd_filename_prefix=output_name,
                    max_retries=retries,
                    dry_run=dry_run,
                )

                # Generate architecture
                arch, error = generator.generate()
                if arch is None:
                    raise ValueError(error or "架构生成失败")

                # Save output
                output_path = generator.save(arch)
                if not output_path:
                    raise ValueError("保存架构文件失败")

                if task.should_stop:
                    task_manager.add_log(task.task_id, "\n⚠️ 任务被用户停止")
                    task_manager.stop_task(task_id)
                else:
                    task_manager.add_log(task.task_id, "\n✅ 架构设计完成！")
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
    task_manager.add_log(task_id, f"项目: {prd_name}")
    task_manager.add_log(task_id, f"工具: {tool}, 重试次数: {retries}, 验证尝试: {max_validation_attempts}")
    if dry_run:
        task_manager.add_log(task_id, "模式: 干跑（不实际调用 AI）")

    return {"task_id": task_id, "status": "started"}


@app.get("/api/events/{task_id}")
async def stream_events(request: Request, task_id: str):
    """Server-Sent Events endpoint for real-time log streaming"""
    task = task_manager.get_task(task_id)
    if not task:
        return StreamingResponse(
            iter(["data: 错误: 任务不存在\n\n"]), media_type="text/event-stream"
        )

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

            # Check if task is done
            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.STOPPED,
            ]:
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
        "prd_name": task.prd_name,
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
        media_type="text/plain",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
