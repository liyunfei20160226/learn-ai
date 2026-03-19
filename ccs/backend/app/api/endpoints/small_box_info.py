"""
FastAPI 路由
自动生成由 ccs-generate
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.small_box_info import SmallBoxInfoResponse, SmallBoxInfoCreate, SmallBoxInfoUpdate
from app.services.small_box_info import SmallBoxInfoService

router = APIRouter(prefix="/small_box_info", tags=["small_box_info"])


@router.get("/", response_model=List[SmallBoxInfoResponse])
def list_small_box_info(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取小箱状况列表"""
    return SmallBoxInfoService.get_all(db, skip, limit)


@router.get("/{id}", response_model=SmallBoxInfoResponse)
def get_small_box_info(id: int, db: Session = Depends(get_db)):
    """根据ID获取小箱状况"""
    obj = SmallBoxInfoService.get_by_id(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="SmallBoxInfo not found")
    return obj


@router.post("/", response_model=SmallBoxInfoResponse)
def create_small_box_info(data: SmallBoxInfoCreate, db: Session = Depends(get_db)):
    """创建小箱状况"""
    return SmallBoxInfoService.create(db, data)


@router.put("/{id}", response_model=SmallBoxInfoResponse)
def update_small_box_info(id: int, data: SmallBoxInfoUpdate, db: Session = Depends(get_db)):
    """更新小箱状况"""
    obj = SmallBoxInfoService.update(db, id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="SmallBoxInfo not found")
    return obj


@router.delete("/{id}")
def delete_small_box_info(id: int, db: Session = Depends(get_db)):
    """删除小箱状况"""
    success = SmallBoxInfoService.delete(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="SmallBoxInfo not found")
    return {"success": True}
