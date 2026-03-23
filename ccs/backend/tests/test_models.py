"""
测试数据模型
验证所有模型能够正确创建
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date, datetime
from sqlalchemy import inspect

from app.models import (
    SmallBoxInfo,
    AcceptanceData,
    ProcessManagement,
    SmallBoxRelation,
    BoxStatus,
)

def test_small_box_info_model():
    """测试 SmallBoxInfo 模型"""
    obj = SmallBoxInfo(
        small_box_no="TEST001",
        system_div="01",
        small_box_type="01",
        arrival_date=date(2024, 1, 1),
        envelope_count=10,
        terminal_count=5,
        remark="测试备注",
        small_box_remark="测试小箱备注",
        register_date=date(2024, 1, 1),
    )
    assert obj.small_box_no == "TEST001"
    assert obj.system_div == "01"
    assert obj.envelope_count == 10
    assert obj.register_date == date(2024, 1, 1)

def test_acceptance_data_model():
    """测试 AcceptanceData 模型"""
    obj = AcceptanceData(
        acceptance_ym="202403",
        small_box_no="TEST001",
        envelope_seq=1,
        line_no=1,
        envelope_no="ENV001",
        registered_no="REG001",
        sales_start_date=date(2024, 1, 1),
        sales_end_date=date(2024, 1, 31),
        terminal_group_no="GROUP01",
        terminal_id_upper="123",
        terminal_id_lower="456",
        maker_no="MAKER01",
        system_div="01",
        new_system_div="02",
        sales_count=10,
        group_cd="GRP01",
        input_date=date(2024, 1, 1),
        input_user_no="USER01",
        envelope_type=1,
        register_date=date(2024, 1, 1),
    )
    assert obj.acceptance_ym == "202403"
    assert obj.small_box_no == "TEST001"
    assert obj.envelope_seq == 1
    assert obj.line_no == 1
    assert obj.sales_count == 10

def test_process_management_model():
    """测试 ProcessManagement 模型"""
    now = datetime.now()
    obj = ProcessManagement(
        small_box_no="TEST001",
        process_div="01",
        personal_code="USER01",
        start_datetime=now,
    )
    assert obj.small_box_no == "TEST001"
    assert obj.process_div == "01"
    assert obj.personal_code == "USER01"
    assert obj.start_datetime == now

def test_small_box_relation_model():
    """测试 SmallBoxRelation 模型"""
    obj = SmallBoxRelation(
        small_box_no="TEST001",
        parent_small_box_no="PARENT001",
        envelope_seq=1,
    )
    assert obj.small_box_no == "TEST001"
    assert obj.parent_small_box_no == "PARENT001"
    assert obj.envelope_seq == 1

def test_box_status_model():
    """测试 BoxStatus 模型"""
    obj = BoxStatus(
        system_div="01",
        small_box_no="TEST001",
        infox_flag=1,
        header_sheet_printed_flag=0,
        scan_system_linked_flag=0,
        small_box_status_cd="ACTIVE",
        small_box_div="01",
        register_date=date(2024, 1, 1),
    )
    assert obj.system_div == "01"
    assert obj.small_box_no == "TEST001"
    assert obj.infox_flag == 1
    assert obj.small_box_div == "01"
    assert obj.register_date == date(2024, 1, 1)
    # 默认值测试
    assert obj.header_sheet_printed_flag == 0
    assert obj.scan_system_linked_flag == 0
