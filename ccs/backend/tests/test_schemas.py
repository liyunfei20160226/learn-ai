"""
测试 Pydantic schemas
验证数据验证功能
"""

from datetime import date, datetime
import pytest
from pydantic import ValidationError

from app.schemas import (
    SmallBoxInfoCreate,
    AcceptanceDataCreate,
    ProcessManagementCreate,
    SmallBoxRelationCreate,
    BoxStatusCreate,
)

def test_small_box_info_create_valid():
    """测试有效的 SmallBoxInfoCreate"""
    data = SmallBoxInfoCreate(
        small_box_no="TEST001",
        system_div="01",
        register_date=date(2024, 1, 1),
    )
    assert data.small_box_no == "TEST001"
    assert data.register_date == date(2024, 1, 1)

def test_small_box_info_create_optional():
    """测试可选字段可以为空"""
    data = SmallBoxInfoCreate(
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    assert data.system_div is None
    assert data.envelope_count is None

def test_acceptance_data_create_valid():
    """测试有效的 AcceptanceDataCreate"""
    data = AcceptanceDataCreate(
        acceptance_ym="202403",
        small_box_no="TEST001",
        envelope_seq=1,
        line_no=1,
        register_date=date(2024, 1, 1),
    )
    assert data.acceptance_ym == "202403"
    assert data.small_box_no == "TEST001"
    assert data.envelope_seq == 1
    assert data.line_no == 1

def test_process_management_create_valid():
    """测试有效的 ProcessManagementCreate"""
    now = datetime.now()
    data = ProcessManagementCreate(
        small_box_no="TEST001",
        process_div="01",
        personal_code="USER01",
        start_datetime=now,
    )
    assert data.small_box_no == "TEST001"
    assert data.process_div == "01"
    assert data.personal_code == "USER01"
    assert data.start_datetime == now

def test_small_box_relation_create_valid():
    """测试有效的 SmallBoxRelationCreate"""
    data = SmallBoxRelationCreate(
        small_box_no="TEST001",
        parent_small_box_no="PARENT001",
        envelope_seq=1,
    )
    assert data.small_box_no == "TEST001"
    assert data.parent_small_box_no == "PARENT001"
    assert data.envelope_seq == 1

def test_box_status_create_valid():
    """测试有效的 BoxStatusCreate"""
    data = BoxStatusCreate(
        system_div="01",
        small_box_no="TEST001",
        infox_flag=1,
        register_date=date(2024, 1, 1),
    )
    assert data.system_div == "01"
    assert data.small_box_no == "TEST001"
    assert data.infox_flag == 1
    assert data.register_date == date(2024, 1, 1)
    # 默认值测试
    assert data.header_sheet_printed_flag == 0
    assert data.scan_system_linked_flag == 0
    assert data.small_box_div == "01"

def test_box_status_create_defaults():
    """测试 BoxStatusCreate 默认值"""
    data = BoxStatusCreate(
        system_div="01",
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    assert data.header_sheet_printed_flag == 0
    assert data.scan_system_linked_flag == 0
    assert data.small_box_div == "01"
