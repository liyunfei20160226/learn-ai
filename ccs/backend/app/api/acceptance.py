"""
受理数据 API 接口
- 销售票据受理数据查询
- 受理数据创建/更新/删除
"""

from typing import Any, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/acceptance", tags=["acceptance"])

@router.get("/{acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}", response_model=schemas.AcceptanceData)
def get_acceptance(
    acceptance_ym: str,
    small_box_no: str,
    envelope_seq: int,
    line_no: int,
    db: Session = Depends(get_db)
):
    """获取单笔受理数据"""
    acceptance = crud.crud_acceptance_data.get(
        db,
        id=(acceptance_ym, small_box_no, envelope_seq, line_no)
    )
    if not acceptance:
        raise HTTPException(
            status_code=404,
            detail=f"受理数据不存在: {acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}"
        )
    return acceptance

@router.get("/", response_model=List[schemas.AcceptanceData])
def list_acceptance(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取受理数据列表（分页）"""
    return crud.crud_acceptance_data.get_multi(db, skip=skip, limit=limit)

@router.get("/by-small-box/{small_box_no}", response_model=List[schemas.AcceptanceData])
def list_acceptance_by_small_box(
    small_box_no: str,
    db: Session = Depends(get_db)
):
    """根据小箱编号获取所有受理数据"""
    return crud.crud_acceptance_data.get_by_small_box_no(db, small_box_no=small_box_no)

@router.post("/", response_model=schemas.AcceptanceData)
def create_acceptance(*, acceptance_in: schemas.AcceptanceDataCreate, db: Session = Depends(get_db)):
    """创建受理数据"""
    existing = crud.crud_acceptance_data.get(
        db,
        id=(
            acceptance_in.acceptance_ym,
            acceptance_in.small_box_no,
            acceptance_in.envelope_seq,
            acceptance_in.line_no,
        )
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"受理数据已存在: {acceptance_in.acceptance_ym}/{acceptance_in.small_box_no}/{acceptance_in.envelope_seq}/{acceptance_in.line_no}"
        )
    return crud.crud_acceptance_data.create(db, obj_in=acceptance_in)

@router.put("/{acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}", response_model=schemas.AcceptanceData)
def update_acceptance(
    acceptance_ym: str,
    small_box_no: str,
    envelope_seq: int,
    line_no: int,
    acceptance_in: schemas.AcceptanceDataUpdate,
    db: Session = Depends(get_db)
):
    """更新受理数据"""
    acceptance = crud.crud_acceptance_data.get(
        db,
        id=(acceptance_ym, small_box_no, envelope_seq, line_no)
    )
    if not acceptance:
        raise HTTPException(
            status_code=404,
            detail=f"受理数据不存在: {acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}"
        )

    # 设置修改日期
    update_data = acceptance_in.model_dump(exclude_unset=True)
    update_data["modify_date"] = date.today()

    return crud.crud_acceptance_data.update(db, db_obj=acceptance, obj_in=update_data)

@router.delete("/{acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}", response_model=schemas.MessageResponse)
def delete_acceptance(
    acceptance_ym: str,
    small_box_no: str,
    envelope_seq: int,
    line_no: int,
    db: Session = Depends(get_db)
):
    """删除受理数据"""
    acceptance = crud.crud_acceptance_data.get(
        db,
        id=(acceptance_ym, small_box_no, envelope_seq, line_no)
    )
    if not acceptance:
        raise HTTPException(
            status_code=404,
            detail=f"受理数据不存在: {acceptance_ym}/{small_box_no}/{envelope_seq}/{line_no}"
        )

    crud.crud_acceptance_data.delete(
        db,
        id=(acceptance_ym, small_box_no, envelope_seq, line_no)
    )
    return {"message": f"受理数据删除成功"}

@router.post("/batch", response_model=List[schemas.AcceptanceData])
def create_acceptance_batch(
    acceptance_list: List[schemas.AcceptanceDataCreate],
    db: Session = Depends(get_db)
):
    """批量创建受理数据"""
    created = []
    for acceptance_in in acceptance_list:
        existing = crud.crud_acceptance_data.get(
            db,
            id=(
                acceptance_in.acceptance_ym,
                acceptance_in.small_box_no,
                acceptance_in.envelope_seq,
                acceptance_in.line_no,
            )
        )
        if existing:
            # 更新而不是创建
            update_data = acceptance_in.model_dump()
            update_data["modify_date"] = date.today()
            updated = crud.crud_acceptance_data.update(db, db_obj=existing, obj_in=update_data)
            created.append(updated)
        else:
            created_item = crud.crud_acceptance_data.create(db, obj_in=acceptance_in)
            created.append(created_item)

    return created
