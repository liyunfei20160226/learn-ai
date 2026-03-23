"""
箱子状态 API 接口
- 箱子状态查询
- 箱子状态更新
"""

from typing import Any, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/status", tags=["status"])

@router.get("/by-small-box/{small_box_no}", response_model=List[schemas.BoxStatus])
def get_box_status_by_small_box(
    small_box_no: str,
    db: Session = Depends(get_db)
):
    """根据小箱编号获取状态"""
    status = crud.crud_box_status.get_by_small_box_no(db, small_box_no=small_box_no)
    return status

@router.get("/{system_div}/{small_box_no}", response_model=schemas.BoxStatus)
def get_box_status(
    system_div: str,
    small_box_no: str,
    db: Session = Depends(get_db)
):
    """获取箱子状态"""
    status = crud.crud_box_status.get(
        db,
        id=(system_div, small_box_no)
    )
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"箱子状态不存在: {system_div}/{small_box_no}"
        )
    return status

@router.post("/", response_model=schemas.BoxStatus)
def create_box_status(*, status_in: schemas.BoxStatusCreate, db: Session = Depends(get_db)):
    """创建箱子状态"""
    existing = crud.crud_box_status.get(
        db,
        id=(status_in.system_div, status_in.small_box_no)
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"箱子状态已存在: {status_in.system_div}/{status_in.small_box_no}"
        )
    return crud.crud_box_status.create(db, obj_in=status_in)

@router.put("/{system_div}/{small_box_no}", response_model=schemas.BoxStatus)
def update_box_status(
    system_div: str,
    small_box_no: str,
    status_in: schemas.BoxStatusUpdate,
    db: Session = Depends(get_db)
):
    """更新箱子状态"""
    status = crud.crud_box_status.get(
        db,
        id=(system_div, small_box_no)
    )
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"箱子状态不存在: {system_div}/{small_box_no}"
        )

    # 设置修改日期
    update_data = status_in.model_dump(exclude_unset=True)
    update_data["modify_date"] = date.today()

    return crud.crud_box_status.update(db, db_obj=status, obj_in=update_data)

@router.delete("/{system_div}/{small_box_no}", response_model=schemas.MessageResponse)
def delete_box_status(
    system_div: str,
    small_box_no: str,
    db: Session = Depends(get_db)
):
    """删除箱子状态"""
    status = crud.crud_box_status.get(
        db,
        id=(system_div, small_box_no)
    )
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"箱子状态不存在: {system_div}/{small_box_no}"
        )

    crud.crud_box_status.delete(
        db,
        id=(system_div, small_box_no)
    )
    return {"message": f"箱子状态删除成功"}
