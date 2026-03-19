"""
业务逻辑 Service
自动生成由 ccs-generate
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.small_box_info import SmallBoxInfo
from app.schemas.small_box_info import SmallBoxInfoCreate, SmallBoxInfoUpdate


class SmallBoxInfoService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[SmallBoxInfo]:
        """获取所有列表"""
        result = db.execute(select(SmallBoxInfo).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    def get_by_id(db: Session, id: int) -> Optional[SmallBoxInfo]:
        """根据ID获取"""
        result = db.execute(select(SmallBoxInfo).where(SmallBoxInfo.id == id))
        return result.scalar_one_or_none()

    @staticmethod
    def create(db: Session, data: SmallBoxInfoCreate) -> SmallBoxInfo:
        """创建"""
        obj = SmallBoxInfo(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, id: int, data: SmallBoxInfoUpdate) -> Optional[SmallBoxInfo]:
        """更新"""
        obj = SmallBoxInfoService.get_by_id(db, id)
        if not obj:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, id: int) -> bool:
        """删除"""
        obj = SmallBoxInfoService.get_by_id(db, id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
