"""
Pydantic Schema
自动生成由 ccs-generate
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class SmallBoxInfoBase(BaseModel):
    small_box_number: int
    parent_small_box_number: Optional[int] = None
    new_system_flag: bool
    arrival_date: Optional[date] = None


class SmallBoxInfoCreate(SmallBoxInfoBase):
    pass


class SmallBoxInfoUpdate(SmallBoxInfoBase):
    pass


class SmallBoxInfoResponse(SmallBoxInfoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
