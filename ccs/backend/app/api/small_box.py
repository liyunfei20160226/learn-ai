"""
小箱相关 API 接口
- 小箱信息查询
- 小箱信息创建/更新/删除
- 小箱状态查询
"""

from typing import Any, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/small-box", tags=["small-box"])

@router.get("/{small_box_no}", response_model=schemas.SmallBoxInfo)
def get_small_box(small_box_no: str, db: Session = Depends(get_db)):
    """根据小箱编号获取小箱信息"""
    small_box = crud.crud_small_box_info.get_by_small_box_no(db, small_box_no=small_box_no)
    if not small_box:
        raise HTTPException(status_code=404, detail=f"小箱 {small_box_no} 不存在")
    return small_box

@router.get("/", response_model=List[schemas.SmallBoxInfo])
def list_small_boxes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取小箱列表（分页）"""
    return crud.crud_small_box_info.get_multi(db, skip=skip, limit=limit)

@router.post("/", response_model=schemas.SmallBoxInfo)
def create_small_box(*, small_box_in: schemas.SmallBoxInfoCreate, db: Session = Depends(get_db)):
    """创建小箱信息"""
    existing = crud.crud_small_box_info.get_by_small_box_no(db, small_box_no=small_box_in.small_box_no)
    if existing:
        raise HTTPException(status_code=400, detail=f"小箱 {small_box_in.small_box_no} 已存在")
    return crud.crud_small_box_info.create(db, obj_in=small_box_in)

@router.put("/{small_box_no}", response_model=schemas.SmallBoxInfo)
def update_small_box(*, small_box_no: str, small_box_in: schemas.SmallBoxInfoUpdate, db: Session = Depends(get_db)):
    """更新小箱信息"""
    small_box = crud.crud_small_box_info.get_by_small_box_no(db, small_box_no=small_box_no)
    if not small_box:
        raise HTTPException(status_code=404, detail=f"小箱 {small_box_no} 不存在")

    # 设置修改日期
    update_data = small_box_in.model_dump(exclude_unset=True)
    update_data["modify_date"] = date.today()

    return crud.crud_small_box_info.update(db, db_obj=small_box, obj_in=update_data)

@router.delete("/{small_box_no}", response_model=schemas.MessageResponse)
def delete_small_box(small_box_no: str, db: Session = Depends(get_db)):
    """删除小箱信息"""
    small_box = crud.crud_small_box_info.get_by_small_box_no(db, small_box_no=small_box_no)
    if not small_box:
        raise HTTPException(status_code=404, detail=f"小箱 {small_box_no} 不存在")

    # 检查有关联数据吗？
    # acceptance_data = crud.crud_acceptance_data.get_by_small_box_no(db, small_box_no=small_box_no)
    # if acceptance_data:
    #     raise HTTPException(status_code=400, detail="小箱存在关联受理数据，无法删除")

    crud.crud_small_box_info.delete(db, id=(small_box_no,))
    return {"message": f"小箱 {small_box_no} 删除成功"}

# 小箱状态
@router.get("/{small_box_no}/status", response_model=List[schemas.BoxStatus])
def get_small_box_status(small_box_no: str, db: Session = Depends(get_db)):
    """获取小箱状态"""
    status = crud.crud_box_status.get_by_small_box_no(db, small_box_no=small_box_no)
    if not status:
        raise HTTPException(status_code=404, detail=f"小箱 {small_box_no} 状态不存在")
    return status

# 获取小箱关联关系
@router.get("/{small_box_no}/relations", response_model=List[schemas.SmallBoxRelation])
def get_small_box_relations(small_box_no: str, db: Session = Depends(get_db)):
    """获取小箱关联关系"""
    relations = crud.crud_small_box_relation.get_by_small_box_no(db, small_box_no=small_box_no)
    return relations

# 获取小箱的受理数据
@router.get("/{small_box_no}/acceptance", response_model=List[schemas.AcceptanceData])
def get_small_box_acceptance(small_box_no: str, db: Session = Depends(get_db)):
    """获取小箱的所有受理数据"""
    data = crud.crud_acceptance_data.get_by_small_box_no(db, small_box_no=small_box_no)
    return data

# 获取小箱的工序管理数据
@router.get("/{small_box_no}/process", response_model=List[schemas.ProcessManagement])
def get_small_box_process(small_box_no: str, db: Session = Depends(get_db)):
    """获取小箱的工序管理数据"""
    data = crud.crud_process_management.get_by_small_box_no(db, small_box_no=small_box_no)
    return data
