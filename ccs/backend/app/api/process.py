"""
工序管理 API 接口
- 工序管理数据查询
- 工序开始/结束记录
"""

from typing import Any, List
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/process", tags=["process"])

@router.get("/{small_box_no}/{process_div}/{personal_code}/{start_datetime}", response_model=schemas.ProcessManagement)
def get_process(
    small_box_no: str,
    process_div: str,
    personal_code: str,
    start_datetime: datetime,
    db: Session = Depends(get_db)
):
    """获取工序记录"""
    process = crud.crud_process_management.get(
        db,
        id=(small_box_no, process_div, personal_code, start_datetime)
    )
    if not process:
        raise HTTPException(
            status_code=404,
            detail=f"工序记录不存在: {small_box_no}/{process_div}/{personal_code}"
        )
    return process

@router.get("/by-small-box/{small_box_no}", response_model=List[schemas.ProcessManagement])
def list_process_by_small_box(
    small_box_no: str,
    db: Session = Depends(get_db)
):
    """根据小箱获取所有工序记录"""
    return crud.crud_process_management.get_by_small_box_no(db, small_box_no=small_box_no)

@router.post("/start", response_model=schemas.ProcessManagement)
def start_process(*, process_in: schemas.ProcessManagementCreate, db: Session = Depends(get_db)):
    """开始工序 - 创建工序记录，设置开始时间"""
    existing = crud.crud_process_management.get(
        db,
        id=(
            process_in.small_box_no,
            process_in.process_div,
            process_in.personal_code,
            process_in.start_datetime,
        )
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"工序记录已存在: {process_in.small_box_no}/{process_in.process_div}/{process_in.personal_code}"
        )
    return crud.crud_process_management.create(db, obj_in=process_in)

@router.put("/end", response_model=schemas.ProcessManagement)
def end_process(*, process_in: schemas.ProcessManagementUpdate, db: Session = Depends(get_db)):
    """结束工序 - 更新结束时间"""
    process = crud.crud_process_management.get(
        db,
        id=(
            process_in.small_box_no,
            process_in.process_div,
            process_in.personal_code,
            process_in.start_datetime,
        )
    )
    if not process:
        raise HTTPException(
            status_code=404,
            detail=f"工序记录不存在: {process_in.small_box_no}/{process_in.process_div}/{process_in.personal_code}"
        )

    # 设置修改日期和结束时间
    update_data = process_in.model_dump(exclude_unset=True)
    update_data["modify_date"] = date.today()

    return crud.crud_process_management.update(db, db_obj=process, obj_in=update_data)

@router.delete("/{small_box_no}/{process_div}/{personal_code}/{start_datetime}", response_model=schemas.MessageResponse)
def delete_process(
    small_box_no: str,
    process_div: str,
    personal_code: str,
    start_datetime: datetime,
    db: Session = Depends(get_db)
):
    """删除工序记录"""
    process = crud.crud_process_management.get(
        db,
        id=(small_box_no, process_div, personal_code, start_datetime)
    )
    if not process:
        raise HTTPException(
            status_code=404,
            detail=f"工序记录不存在: {small_box_no}/{process_div}/{personal_code}/{start_datetime}"
        )

    crud.crud_process_management.delete(
        db,
        id=(small_box_no, process_div, personal_code, start_datetime)
    )
    return {"message": f"工序记录删除成功"}
