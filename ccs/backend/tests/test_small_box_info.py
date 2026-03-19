"""
pytest 测试 - 100% 覆盖率要求
自动生成由 ccs-generate
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from main import app
from app.models.small_box_info import SmallBoxInfo


@pytest.mark.asyncio
async def test_list_small_box_info(client: AsyncClient, db: Session):
    """测试获取列表"""
    response = await client.get("/api/small_box_info/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_and_get_small_box_info(client: AsyncClient, db: Session):
    """测试创建和获取"""
    create_data = {
        "small_box_number": 12345,
        "parent_small_box_number": 123,
        "new_system_flag": True,
        "arrival_date": "2024-01-01",
    }
    response = await client.post("/api/small_box_info/", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["small_box_number"] == create_data["small_box_number"]
    assert data["parent_small_box_number"] == create_data["parent_small_box_number"]
    assert data["new_system_flag"] == create_data["new_system_flag"]
    assert data["arrival_date"] == create_data["arrival_date"]

    # 获取
    id = data["id"]
    response = await client.get(f"/api/small_box_info/{id}")
    assert response.status_code == 200
    assert response.json()["id"] == id


@pytest.mark.asyncio
async def test_update_small_box_info(client: AsyncClient, db: Session):
    """测试更新"""
    # 先创建
    create_data = {
        "small_box_number": 12345,
        "parent_small_box_number": 123,
        "new_system_flag": True,
        "arrival_date": "2024-01-01",
    }
    response = await client.post("/api/small_box_info/", json=create_data)
    id = response.json()["id"]

    # 更新
    update_data = {
        "small_box_number": 67890,
        "parent_small_box_number": 456,
        "new_system_flag": False,
        "arrival_date": "2024-02-01",
    }
    response = await client.put(f"/api/small_box_info/{id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["small_box_number"] == update_data["small_box_number"]
    assert response.json()["parent_small_box_number"] == update_data["parent_small_box_number"]
    assert response.json()["new_system_flag"] == update_data["new_system_flag"]
    assert response.json()["arrival_date"] == update_data["arrival_date"]


@pytest.mark.asyncio
async def test_delete_small_box_info(client: AsyncClient, db: Session):
    """测试删除"""
    # 先创建
    create_data = {
        "small_box_number": 12345,
        "parent_small_box_number": 123,
        "new_system_flag": True,
        "arrival_date": "2024-01-01",
    }
    response = await client.post("/api/small_box_info/", json=create_data)
    id = response.json()["id"]

    # 删除
    response = await client.delete(f"/api/small_box_info/{id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # 确认已删除
    response = await client.get(f"/api/small_box_info/{id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_small_box_info_not_found(client: AsyncClient, db: Session):
    """测试获取不存在的ID返回404"""
    response = await client.get("/api/small_box_info/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_small_box_info_not_found(client: AsyncClient, db: Session):
    """测试更新不存在的ID返回404"""
    update_data = {
        "small_box_number": 12345,
        "parent_small_box_number": 123,
        "new_system_flag": True,
        "arrival_date": "2024-01-01",
    }
    response = await client.put("/api/small_box_info/99999", json=update_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_small_box_info_not_found(client: AsyncClient, db: Session):
    """测试删除不存在的ID返回404"""
    response = await client.delete("/api/small_box_info/99999")
    assert response.status_code == 404
