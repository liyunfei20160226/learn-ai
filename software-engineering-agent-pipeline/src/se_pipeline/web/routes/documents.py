"""
Document upload and delete routes
"""
from pathlib import Path
from fastapi import Request, APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.web.templates import templates

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
    from se_pipeline.types.pipeline import AttachedDocument
    updated = False

    for upload_file in files:
        # 安全处理文件名
        filename = Path(upload_file.filename).name
        # 替换不安全字符
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._ -()[]")
        if not safe_filename:
            continue

        file_path = uploads_dir / safe_filename
        file_size = 0
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            file_size = len(content)
            f.write(content)

        # 添加到 attached_documents 列表
        doc = AttachedDocument(
            filename=safe_filename,
            relative_path=str(file_path.relative_to(project_dir)),
            absolute_path=str(file_path),
            original_ext=Path(safe_filename).suffix,
            file_size=file_size,
            parse_success=True,
        )
        # 创建新列表避免修改原对象
        new_docs = list(state.attached_documents)
        new_docs.append(doc)
        state = state.model_copy(update={"attached_documents": new_docs})
        updated = True

    # 更新 source_documents_dir
    if not state.source_documents_dir:
        state = state.model_copy(update={"source_documents_dir": str(uploads_dir)})

    if updated:
        # 上传新文档后，重置文档处理标记，需要重新预处理
        # 这样新上传的文档会被整合到项目背景中
        state = state.model_copy(update={
            "documents_processed": False,
        })
        store.save_state(project_id, state)

    # 返回更新后的文档列表
    return templates.TemplateResponse(request, "components/document_list.html.jinja", {
        "state": state,
        "project_id": project_id,
        "requirements_already_completed": state.requirements_spec is not None,
    })


@router.delete("/projects/{project_id}/documents/{filename}")
async def delete_document(request: Request, project_id: str, filename: str):
    """删除上传的文档"""
    state = store.load_state(project_id)
    if state is None:
        return HTMLResponse("<div class='text-red-600'>项目不存在</div>", status_code=404)

    # 从 attached_documents 中移除
    new_docs = [doc for doc in state.attached_documents if doc.filename != filename]
    state = state.model_copy(update={"attached_documents": new_docs})
    # 删除文档后，重置文档处理标记，需要重新预处理
    state = state.model_copy(update={
        "documents_processed": False,
    })
    store.save_state(project_id, state)

    # 删除物理文件
    project_dir = store.get_project_dir(project_id)
    uploads_dir = project_dir / "uploads"
    file_path = uploads_dir / filename
    if file_path.exists():
        file_path.unlink()

    # 返回更新后的文档列表
    return templates.TemplateResponse(request, "components/document_list.html.jinja", {
        "state": state,
        "project_id": project_id,
        "requirements_already_completed": state.requirements_spec is not None,
    })
