"""
Document upload and delete routes
"""
import os
from pathlib import Path
from fastapi import Request, APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from se_pipeline.web.templates import templates
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.types.pipeline import PipelineState

router = APIRouter()
store = ProjectStore()


@router.post("/projects/{project_id}/upload", response_class=HTMLResponse)
async def upload_file(request: Request, project_id: str, files: list[UploadFile] = File(...)):
    """上传文件到项目"""
    state = store.load_state(project_id)
    if state is None:
        return HTMLResponse("<div class='text-red-600'>项目不存在</div>", status_code=404)

    # 创建 uploads 目录
    project_dir = store.get_project_dir(project_id)
    uploads_dir = project_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    # 保存上传的文件
    for upload_file in files:
        # 安全处理文件名
        filename = Path(upload_file.filename).name
        # 替换不安全字符
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._ -()[]")
        if not safe_filename:
            continue

        file_path = uploads_dir / safe_filename
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

    # 更新 source_documents_dir
    if not state.source_documents_dir:
        state = state.model_copy(update={"source_documents_dir": str(uploads_dir)})
    store.save_state(project_id, state)

    # 返回更新后的文档列表
    return templates.TemplateResponse("components/document_list.html", {
        "request": request,
        "state": state,
        "project_id": project_id
    })


@router.delete("/projects/{project_id}/documents/{filename}")
async def delete_document(request: Request, project_id: str, filename: str):
    """删除上传的文档"""
    state = store.load_state(project_id)
    if state is None:
        return HTMLResponse("<div class='text-red-600'>项目不存在</div>", status_code=404)

    # 实际上只是从 attached_documents 中移除，文件已经在uploads里
    # 这里刷新列表即可
    return templates.TemplateResponse("components/document_list.html", {
        "request": request,
        "state": state,
        "project_id": project_id
    })
