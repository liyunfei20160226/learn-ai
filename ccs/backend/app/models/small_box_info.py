"""
SQLAlchemy 模型
自动生成由 ccs-generate
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Text, func
from app.core.database import Base


class SmallBoxInfo(Base):
    __tablename__ = "small_box_info"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    small_box_number = Column(Integer, nullable=False, comment="小箱编号")
    parent_small_box_number = Column(Integer, comment="父小箱编号")
    new_system_flag = Column(Boolean, nullable=False, default=False, comment="新系统区分")
    arrival_date = Column(Date, comment="到达日期")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=func.now(), comment="更新时间")
