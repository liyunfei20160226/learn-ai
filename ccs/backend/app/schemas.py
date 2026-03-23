"""
Pydantic schemas - 数据验证 schema
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

# ======================================
# SmallBoxInfo - 小箱信息
# ======================================
class SmallBoxInfoBase(BaseModel):
    system_div: Optional[str] = None
    small_box_type: Optional[str] = None
    arrival_date: Optional[date] = None
    envelope_count: Optional[int] = None
    terminal_count: Optional[int] = None
    remark: Optional[str] = None
    small_box_remark: Optional[str] = None

class SmallBoxInfoCreate(SmallBoxInfoBase):
    small_box_no: str
    register_date: date

class SmallBoxInfoUpdate(SmallBoxInfoBase):
    small_box_no: Optional[str] = None
    register_date: Optional[date] = None
    modify_date: Optional[date] = None

class SmallBoxInfo(SmallBoxInfoBase):
    small_box_no: str
    register_date: date
    modify_date: Optional[date] = None

    class Config:
        from_attributes = True

# ======================================
# AcceptanceData - 受理数据
# ======================================
class AcceptanceDataBase(BaseModel):
    envelope_no: Optional[str] = None
    registered_no: Optional[str] = None
    sales_start_date: Optional[date] = None
    sales_end_date: Optional[date] = None
    terminal_group_no: Optional[str] = None
    terminal_id_upper: Optional[str] = None
    terminal_id_lower: Optional[str] = None
    maker_no: Optional[str] = None
    system_div: Optional[str] = None
    new_system_div: Optional[str] = None
    sales_count: Optional[int] = None
    group_cd: Optional[str] = None
    input_date: Optional[date] = None
    input_user_no: Optional[str] = None
    envelope_type: Optional[int] = None
    modify_user_no: Optional[str] = None

class AcceptanceDataCreate(AcceptanceDataBase):
    acceptance_ym: str
    small_box_no: str
    envelope_seq: int
    line_no: int
    register_date: date

class AcceptanceDataUpdate(AcceptanceDataBase):
    acceptance_ym: Optional[str] = None
    small_box_no: Optional[str] = None
    envelope_seq: Optional[int] = None
    line_no: Optional[int] = None
    register_date: Optional[date] = None
    modify_date: Optional[date] = None

class AcceptanceData(AcceptanceDataBase):
    acceptance_ym: str
    small_box_no: str
    envelope_seq: int
    line_no: int
    register_date: date
    modify_date: Optional[date] = None

    class Config:
        from_attributes = True

# ======================================
# ProcessManagement - 工序管理
# ======================================
class ProcessManagementBase(BaseModel):
    end_datetime: Optional[datetime] = None
    work_time: Optional[str] = None  # Interval
    modify_date: Optional[date] = None

class ProcessManagementCreate(ProcessManagementBase):
    small_box_no: str
    process_div: str
    personal_code: str
    start_datetime: datetime

class ProcessManagementUpdate(ProcessManagementBase):
    small_box_no: Optional[str] = None
    process_div: Optional[str] = None
    personal_code: Optional[str] = None
    start_datetime: Optional[datetime] = None

class ProcessManagement(ProcessManagementBase):
    small_box_no: str
    process_div: str
    personal_code: str
    start_datetime: datetime

    class Config:
        from_attributes = True

# ======================================
# SmallBoxRelation - 小箱关联
# ======================================
class SmallBoxRelationBase(BaseModel):
    pass

class SmallBoxRelationCreate(SmallBoxRelationBase):
    small_box_no: str
    parent_small_box_no: str
    envelope_seq: int

class SmallBoxRelationUpdate(SmallBoxRelationBase):
    small_box_no: Optional[str] = None
    parent_small_box_no: Optional[str] = None
    envelope_seq: Optional[int] = None

class SmallBoxRelation(SmallBoxRelationBase):
    small_box_no: str
    parent_small_box_no: str
    envelope_seq: int

    class Config:
        from_attributes = True

# ======================================
# BoxStatus - 箱子状态
# ======================================
class BoxStatusBase(BaseModel):
    infox_flag: Optional[int] = None
    header_sheet_printed_flag: Optional[int] = 0
    scan_system_linked_flag: Optional[int] = 0
    small_box_status_cd: Optional[str] = None
    small_box_div: Optional[str] = "01"

class BoxStatusCreate(BoxStatusBase):
    system_div: str
    small_box_no: str
    register_date: date

class BoxStatusUpdate(BoxStatusBase):
    system_div: Optional[str] = None
    small_box_no: Optional[str] = None
    register_date: Optional[date] = None
    modify_date: Optional[date] = None

class BoxStatus(BoxStatusBase):
    system_div: str
    small_box_no: str
    register_date: date
    modify_date: Optional[date] = None

    class Config:
        from_attributes = True

# ======================================
# 通用响应
# ======================================
class PaginationResponse(BaseModel):
    total: int
    page: int
    size: int
    data: list

class MessageResponse(BaseModel):
    message: str
