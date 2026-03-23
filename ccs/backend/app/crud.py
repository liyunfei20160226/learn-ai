"""
CRUD 操作 - 通用数据库操作
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD 基类，提供通用 CRUD 操作
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """根据主键获取"""
        return db.query(self.model).get(id)

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """分页获取"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def count(self, db: Session) -> int:
        """计数"""
        return db.query(self.model).count()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """创建"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """更新"""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: Any) -> ModelType:
        """删除"""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj

# ======================================
# 具体 CRUD
# ======================================
from .models import (
    SmallBoxInfo,
    AcceptanceData,
    ProcessManagement,
    SmallBoxRelation,
    BoxStatus,
)
from .schemas import (
    SmallBoxInfoCreate,
    SmallBoxInfoUpdate,
    AcceptanceDataCreate,
    AcceptanceDataUpdate,
    ProcessManagementCreate,
    ProcessManagementUpdate,
    SmallBoxRelationCreate,
    SmallBoxRelationUpdate,
    BoxStatusCreate,
    BoxStatusUpdate,
)

class CRUDSmallBoxInfo(CRUDBase[SmallBoxInfo, SmallBoxInfoCreate, SmallBoxInfoUpdate]):
    def get_by_small_box_no(self, db: Session, *, small_box_no: str) -> Optional[SmallBoxInfo]:
        return db.query(SmallBoxInfo).filter(SmallBoxInfo.small_box_no == small_box_no).first()

class CRUDAcceptanceData(CRUDBase[AcceptanceData, AcceptanceDataCreate, AcceptanceDataUpdate]):
    def get_by_small_box_no(self, db: Session, *, small_box_no: str) -> List[AcceptanceData]:
        return db.query(AcceptanceData).filter(AcceptanceData.small_box_no == small_box_no).all()

    def count_by_small_box_no(self, db: Session, *, small_box_no: str) -> int:
        return db.query(AcceptanceData).filter(AcceptanceData.small_box_no == small_box_no).count()

class CRUDProcessManagement(CRUDBase[ProcessManagement, ProcessManagementCreate, ProcessManagementUpdate]):
    def get_by_small_box_no(self, db: Session, *, small_box_no: str) -> List[ProcessManagement]:
        return db.query(ProcessManagement).filter(ProcessManagement.small_box_no == small_box_no).all()

class CRUDSmallBoxRelation(CRUDBase[SmallBoxRelation, SmallBoxRelationCreate, SmallBoxRelationUpdate]):
    def get_by_small_box_no(self, db: Session, *, small_box_no: str) -> List[SmallBoxRelation]:
        return db.query(SmallBoxRelation).filter(SmallBoxRelation.small_box_no == small_box_no).all()

class CRUDBoxStatus(CRUDBase[BoxStatus, BoxStatusCreate, BoxStatusUpdate]):
    def get_by_small_box_no(self, db: Session, *, small_box_no: str) -> List[BoxStatus]:
        return db.query(BoxStatus).filter(BoxStatus.small_box_no == small_box_no).all()

# 实例化
crud_small_box_info = CRUDSmallBoxInfo(SmallBoxInfo)
crud_acceptance_data = CRUDAcceptanceData(AcceptanceData)
crud_process_management = CRUDProcessManagement(ProcessManagement)
crud_small_box_relation = CRUDSmallBoxRelation(SmallBoxRelation)
crud_box_status = CRUDBoxStatus(BoxStatus)
