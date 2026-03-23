"""
测试 受理数据 API 接口
"""

from datetime import date
from fastapi.testclient import TestClient

def test_get_acceptance_not_found(client: TestClient):
    """测试获取不存在的受理数据"""
    response = client.get("/api/acceptance/202403/TEST001/1/1")
    assert response.status_code == 404

def test_create_acceptance(client: TestClient):
    """测试创建受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TEST001",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TEST001",
        "envelope_seq": 1,
        "line_no": 1,
        "sales_count": 10,
        "register_date": "2024-01-01",
    }
    response = client.post("/api/acceptance/", json=acceptance_data)
    assert response.status_code == 200
    result = response.json()
    assert result["acceptance_ym"] == "202403"
    assert result["sales_count"] == 10

def test_create_acceptance_duplicate(client: TestClient):
    """测试创建重复受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDUP",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 第一次创建
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTDUP",
        "envelope_seq": 1,
        "line_no": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 第二次创建应该失败
    response = client.post("/api/acceptance/", json=acceptance_data)
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]

def test_get_acceptance(client: TestClient):
    """测试获取受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TEST002",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TEST002",
        "envelope_seq": 1,
        "line_no": 1,
        "sales_count": 10,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 获取
    response = client.get("/api/acceptance/202403/TEST002/1/1")
    assert response.status_code == 200
    result = response.json()
    assert result["acceptance_ym"] == "202403"
    assert result["sales_count"] == 10

def test_list_acceptance(client: TestClient):
    """测试获取受理数据列表"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTLIST",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建几个受理数据
    for i in range(3):
        acceptance_data = {
            "acceptance_ym": "202403",
            "small_box_no": "TESTLIST",
            "envelope_seq": i + 1,
            "line_no": 1,
            "sales_count": 10,
            "register_date": "2024-01-01",
        }
        client.post("/api/acceptance/", json=acceptance_data)

    response = client.get("/api/acceptance/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 3

def test_list_acceptance_by_small_box(client: TestClient):
    """测试按小箱获取受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTBYBOX",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTBYBOX",
        "envelope_seq": 1,
        "line_no": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    response = client.get("/api/acceptance/by-small-box/TESTBYBOX")
    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 1

def test_update_acceptance(client: TestClient):
    """测试更新受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTUPDATE",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTUPDATE",
        "envelope_seq": 1,
        "line_no": 1,
        "sales_count": 10,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 更新
    update_data = {
        "sales_count": 20,
    }
    response = client.put("/api/acceptance/202403/TESTUPDATE/1/1", json=update_data)
    assert response.status_code == 200
    result = response.json()
    assert result["sales_count"] == 20
    assert result["modify_date"] is not None

def test_delete_acceptance(client: TestClient):
    """测试删除受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDELETE",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTDELETE",
        "envelope_seq": 1,
        "line_no": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 删除
    response = client.delete("/api/acceptance/202403/TESTDELETE/1/1")
    assert response.status_code == 200
    result = response.json()
    assert "删除成功" in result["message"]

    # 确认已删除
    response = client.get("/api/acceptance/202403/TESTDELETE/1/1")
    assert response.status_code == 404

def test_delete_acceptance_not_found(client: TestClient):
    """测试删除不存在的受理数据"""
    response = client.delete("/api/acceptance/202403/NOTEXIST/1/1")
    assert response.status_code == 404

def test_create_acceptance_batch(client: TestClient):
    """测试批量创建受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTBATCH",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 批量创建
    batch_data = [
        {
            "acceptance_ym": "202403",
            "small_box_no": "TESTBATCH",
            "envelope_seq": 1,
            "line_no": 1,
            "sales_count": 10,
            "register_date": "2024-01-01",
        },
        {
            "acceptance_ym": "202403",
            "small_box_no": "TESTBATCH",
            "envelope_seq": 2,
            "line_no": 1,
            "sales_count": 20,
            "register_date": "2024-01-01",
        },
    ]
    response = client.post("/api/acceptance/batch", json=batch_data)
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2

def test_create_acceptance_batch_with_existing(client: TestClient):
    """测试批量创建受理数据（包含已存在，会走更新分支）"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTBATCH2",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 先创建第一个
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTBATCH2",
        "envelope_seq": 1,
        "line_no": 1,
        "sales_count": 10,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 批量创建，其中一个已存在，应该更新而不是创建
    batch_data = [
        {
            "acceptance_ym": "202403",
            "small_box_no": "TESTBATCH2",
            "envelope_seq": 1,
            "line_no": 1,
            "sales_count": 99,
            "register_date": "2024-01-01",
        },
        {
            "acceptance_ym": "202403",
            "small_box_no": "TESTBATCH2",
            "envelope_seq": 2,
            "line_no": 1,
            "sales_count": 20,
            "register_date": "2024-01-01",
        },
    ]
    response = client.post("/api/acceptance/batch", json=batch_data)
    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2
    # 第一个应该被更新为 99
    assert any(item["sales_count"] == 99 for item in result)
