"""
测试 CRUD 操作
验证数据库操作
"""

from datetime import date
import pytest
from sqlalchemy.orm import Session

from app import crud, models, schemas

def test_crud_small_box_info(db_session: Session):
    """测试 SmallBoxInfo CRUD"""
    # 创建
    small_box_in = schemas.SmallBoxInfoCreate(
        small_box_no="TEST001",
        system_div="01",
        register_date=date(2024, 1, 1),
    )
    obj = crud.crud_small_box_info.create(db_session, obj_in=small_box_in)
    assert obj.small_box_no == "TEST001"

    # 获取
    obj_get = crud.crud_small_box_info.get_by_small_box_no(db_session, small_box_no="TEST001")
    assert obj_get is not None
    assert obj_get.small_box_no == "TEST001"

    # 更新
    update_in = schemas.SmallBoxInfoUpdate(
        envelope_count=10,
        terminal_count=5,
        modify_date=date.today(),
    )
    obj_updated = crud.crud_small_box_info.update(db_session, db_obj=obj, obj_in=update_in)
    assert obj_updated.envelope_count == 10
    assert obj_updated.terminal_count == 5
    assert obj_updated.modify_date is not None

    # 分页列表
    list_objs = crud.crud_small_box_info.get_multi(db_session, skip=0, limit=10)
    assert len(list_objs) >= 1

    # 计数
    count = crud.crud_small_box_info.count(db_session)
    assert count >= 1

    # 删除
    crud.crud_small_box_info.delete(db_session, id=("TEST001",))
    obj_deleted = crud.crud_small_box_info.get_by_small_box_no(db_session, small_box_no="TEST001")
    assert obj_deleted is None

def test_crud_acceptance_data(db_session: Session):
    """测试 AcceptanceData CRUD"""
    # 先创建小箱
    small_box_in = schemas.SmallBoxInfoCreate(
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    crud.crud_small_box_info.create(db_session, obj_in=small_box_in)

    # 创建受理数据
    acceptance_in = schemas.AcceptanceDataCreate(
        acceptance_ym="202403",
        small_box_no="TEST001",
        envelope_seq=1,
        line_no=1,
        sales_count=10,
        register_date=date(2024, 1, 1),
    )
    obj = crud.crud_acceptance_data.create(db_session, obj_in=acceptance_in)
    assert obj.acceptance_ym == "202403"
    assert obj.small_box_no == "TEST001"

    # 获取
    obj_get = crud.crud_acceptance_data.get(
        db_session,
        id=("202403", "TEST001", 1, 1),
    )
    assert obj_get is not None

    # 按小箱获取
    list_by_box = crud.crud_acceptance_data.get_by_small_box_no(
        db_session,
        small_box_no="TEST001",
    )
    assert len(list_by_box) >= 1

    # 计数按小箱
    count = crud.crud_acceptance_data.count_by_small_box_no(db_session, small_box_no="TEST001")
    assert count >= 1

    # 更新
    update_in = schemas.AcceptanceDataUpdate(
        sales_count=20,
        modify_date=date.today(),
    )
    obj_updated = crud.crud_acceptance_data.update(
        db_session,
        db_obj=obj,
        obj_in=update_in,
    )
    assert obj_updated.sales_count == 20
    assert obj_updated.modify_date is not None

    # 删除
    crud.crud_acceptance_data.delete(
        db_session,
        id=("202403", "TEST001", 1, 1),
    )
    obj_deleted = crud.crud_acceptance_data.get(
        db_session,
        id=("202403", "TEST001", 1, 1),
    )
    assert obj_deleted is None

def test_crud_process_management(db_session: Session):
    """测试 ProcessManagement CRUD"""
    from datetime import datetime
    # 先创建小箱
    small_box_in = schemas.SmallBoxInfoCreate(
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    crud.crud_small_box_info.create(db_session, obj_in=small_box_in)

    now = datetime.now()
    process_in = schemas.ProcessManagementCreate(
        small_box_no="TEST001",
        process_div="01",
        personal_code="USER01",
        start_datetime=now,
    )
    obj = crud.crud_process_management.create(db_session, obj_in=process_in)
    assert obj.small_box_no == "TEST001"

    # 获取
    obj_get = crud.crud_process_management.get(
        db_session,
        id=("TEST001", "01", "USER01", now),
    )
    assert obj_get is not None

    # 按小箱获取
    list_by_box = crud.crud_process_management.get_by_small_box_no(
        db_session,
        small_box_no="TEST001",
    )
    assert len(list_by_box) >= 1

def test_crud_small_box_relation(db_session: Session):
    """测试 SmallBoxRelation CRUD"""
    # 创建两个小箱
    small_box_in1 = schemas.SmallBoxInfoCreate(
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    small_box_in2 = schemas.SmallBoxInfoCreate(
        small_box_no="PARENT001",
        register_date=date(2024, 1, 1),
    )
    crud.crud_small_box_info.create(db_session, obj_in=small_box_in1)
    crud.crud_small_box_info.create(db_session, obj_in=small_box_in2)

    relation_in = schemas.SmallBoxRelationCreate(
        small_box_no="TEST001",
        parent_small_box_no="PARENT001",
        envelope_seq=1,
    )
    obj = crud.crud_small_box_relation.create(db_session, obj_in=relation_in)
    assert obj.small_box_no == "TEST001"
    assert obj.parent_small_box_no == "PARENT001"

    # 获取
    list_by_box = crud.crud_small_box_relation.get_by_small_box_no(
        db_session,
        small_box_no="TEST001",
    )
    assert len(list_by_box) >= 1

def test_crud_box_status(db_session: Session):
    """测试 BoxStatus CRUD"""
    # 先创建小箱
    small_box_in = schemas.SmallBoxInfoCreate(
        small_box_no="TEST001",
        register_date=date(2024, 1, 1),
    )
    crud.crud_small_box_info.create(db_session, obj_in=small_box_in)

    status_in = schemas.BoxStatusCreate(
        system_div="01",
        small_box_no="TEST001",
        infox_flag=1,
        register_date=date(2024, 1, 1),
    )
    obj = crud.crud_box_status.create(db_session, obj_in=status_in)
    assert obj.system_div == "01"
    assert obj.small_box_no == "TEST001"
    assert obj.infox_flag == 1

    # 获取
    obj_get_list = crud.crud_box_status.get_by_small_box_no(
        db_session,
        small_box_no="TEST001",
    )
    assert len(obj_get_list) >= 1
    obj_get = obj_get_list[0]
    assert obj_get.infox_flag == 1

    # 更新
    update_in = schemas.BoxStatusUpdate(
        infox_flag=0,
        modify_date=date.today(),
    )
    obj_updated = crud.crud_box_status.update(db_session, db_obj=obj, obj_in=update_in)
    assert obj_updated.infox_flag == 0
    assert obj_updated.modify_date is not None
