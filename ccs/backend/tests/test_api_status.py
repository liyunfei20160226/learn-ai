"""
测试 箱子状态 API 接口
"""

from datetime import date
from fastapi.testclient import TestClient

def test_get_box_status_not_found(client: TestClient):
    """测试获取不存在的状态"""
    response = client.get("/api/status/01/NOTEXIST")
    assert response.status_code == 404

def test_create_box_status(client: TestClient):
    """测试创建箱子状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TEST001",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TEST001",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    response = client.post("/api/status/", json=status_data)
    assert response.status_code == 200
    result = response.json()
    assert result["system_div"] == "01"
    assert result["small_box_no"] == "TEST001"
    assert result["infox_flag"] == 1

def test_create_box_status_duplicate(client: TestClient):
    """测试创建重复状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDUP",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TESTDUP",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/status/", json=status_data)
    # 第二次创建应该失败
    response = client.post("/api/status/", json=status_data)
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]

def test_get_box_status(client: TestClient):
    """测试获取箱子状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TEST002",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TEST002",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/status/", json=status_data)

    response = client.get("/api/status/01/TEST002")
    assert response.status_code == 200
    result = response.json()
    assert result["infox_flag"] == 1

def test_get_box_status_by_small_box(client: TestClient):
    """测试按小箱编号获取状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTBYBOX",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    resp1 = client.post("/api/small-box/", json=small_box_data)
    assert resp1.status_code == 200

    status_data = {
        "system_div": "01",
        "small_box_no": "TESTBYBOX",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    resp2 = client.post("/api/status/", json=status_data)
    assert resp2.status_code == 200, f"create status failed: {resp2.content}"

    response = client.get("/api/status/by-small-box/TESTBYBOX")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["small_box_no"] == "TESTBYBOX"

def test_update_box_status(client: TestClient):
    """测试更新箱子状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTUPDATE",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TESTUPDATE",
        "infox_flag": 0,
        "register_date": "2024-01-01",
    }
    client.post("/api/status/", json=status_data)

    # 更新
    update_data = {
        "infox_flag": 1,
        "header_sheet_printed_flag": 1,
    }
    response = client.put("/api/status/01/TESTUPDATE", json=update_data)
    assert response.status_code == 200
    result = response.json()
    assert result["infox_flag"] == 1
    assert result["header_sheet_printed_flag"] == 1
    assert result["modify_date"] is not None

def test_delete_box_status(client: TestClient):
    """测试删除箱子状态"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDELETE",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TESTDELETE",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/status/", json=status_data)

    # 删除
    response = client.delete("/api/status/01/TESTDELETE")
    assert response.status_code == 200
    result = response.json()
    assert "删除成功" in result["message"]

    # 确认已删除
    response = client.get("/api/status/01/TESTDELETE")
    assert response.status_code == 404

def test_box_status_default_values(client: TestClient):
    """测试箱子状态默认值"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDEFAULT",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    status_data = {
        "system_div": "01",
        "small_box_no": "TESTDEFAULT",
        "register_date": "2024-01-01",
    }
    response = client.post("/api/status/", json=status_data)
    result = response.json()
    # 默认值测试
    assert result["header_sheet_printed_flag"] == 0
    assert result["scan_system_linked_flag"] == 0
    assert result["small_box_div"] == "01"

def test_update_box_status_not_found(client: TestClient):
    """测试更新不存在的箱子状态"""
    update_data = {
        "infox_flag": 1,
    }
    response = client.put("/api/status/01/NOTEXIST", json=update_data)
    assert response.status_code == 404

def test_delete_box_status_not_found(client: TestClient):
    """测试删除不存在的箱子状态"""
    response = client.delete("/api/status/01/NOTEXIST")
    assert response.status_code == 404
