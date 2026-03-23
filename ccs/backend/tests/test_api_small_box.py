"""
测试 小箱 API 接口
"""

from datetime import date
from fastapi.testclient import TestClient

def test_get_small_box_not_found(client: TestClient):
    """测试获取不存在的小箱"""
    response = client.get("/api/small-box/NOTEXIST")
    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]

def test_create_small_box(client: TestClient):
    """测试创建小箱"""
    data = {
        "small_box_no": "TEST001",
        "system_div": "01",
        "small_box_type": "01",
        "arrival_date": "2024-01-01",
        "envelope_count": 10,
        "terminal_count": 5,
        "remark": "测试备注",
        "register_date": "2024-01-01",
    }
    response = client.post("/api/small-box/", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["small_box_no"] == "TEST001"
    assert result["envelope_count"] == 10

def test_create_small_box_duplicate(client: TestClient):
    """测试创建重复小箱应该返回错误"""
    data = {
        "small_box_no": "TESTDUP",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    # 第一次创建
    client.post("/api/small-box/", json=data)
    # 第二次创建应该失败
    response = client.post("/api/small-box/", json=data)
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]

def test_get_small_box(client: TestClient):
    """测试获取小箱信息"""
    # 先创建
    data = {
        "small_box_no": "TEST002",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=data)

    # 获取
    response = client.get("/api/small-box/TEST002")
    assert response.status_code == 200
    result = response.json()
    assert result["small_box_no"] == "TEST002"

def test_list_small_boxes(client: TestClient):
    """测试获取小箱列表"""
    # 创建几个
    for i in range(3):
        data = {
            "small_box_no": f"LIST{i:03d}",
            "system_div": "01",
            "register_date": "2024-01-01",
        }
        client.post("/api/small-box/", json=data)

    response = client.get("/api/small-box/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 3

def test_update_small_box(client: TestClient):
    """测试更新小箱"""
    # 先创建
    data = {
        "small_box_no": "TESTUPDATE",
        "system_div": "01",
        "register_date": "2024-01-01",
        "envelope_count": 5,
    }
    client.post("/api/small-box/", json=data)

    # 更新
    update_data = {
        "envelope_count": 10,
        "terminal_count": 5,
    }
    response = client.put("/api/small-box/TESTUPDATE", json=update_data)
    assert response.status_code == 200
    result = response.json()
    assert result["envelope_count"] == 10
    assert result["terminal_count"] == 5
    assert result["modify_date"] is not None

def test_delete_small_box(client: TestClient):
    """测试删除小箱"""
    # 先创建
    data = {
        "small_box_no": "TESTDELETE",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=data)

    # 删除
    response = client.delete("/api/small-box/TESTDELETE")
    assert response.status_code == 200
    result = response.json()
    assert "删除成功" in result["message"]

    # 确认已删除
    response = client.get("/api/small-box/TESTDELETE")
    assert response.status_code == 404

def test_delete_small_box_not_found(client: TestClient):
    """测试删除不存在的小箱"""
    response = client.delete("/api/small-box/NOTEXIST")
    assert response.status_code == 404

def test_get_small_box_status(client: TestClient):
    """测试获取小箱状态"""
    from datetime import date
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTSTATUS",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建状态
    status_data = {
        "system_div": "01",
        "small_box_no": "TESTSTATUS",
        "infox_flag": 1,
        "register_date": "2024-01-01",
    }
    client.post("/api/status/", json=status_data)

    # 获取状态
    response = client.get("/api/small-box/TESTSTATUS/status")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0]["infox_flag"] == 1

def test_get_small_box_acceptance(client: TestClient):
    """测试获取小箱受理数据"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTACCEPT",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建受理数据
    acceptance_data = {
        "acceptance_ym": "202403",
        "small_box_no": "TESTACCEPT",
        "envelope_seq": 1,
        "line_no": 1,
        "sales_count": 10,
        "register_date": "2024-01-01",
    }
    client.post("/api/acceptance/", json=acceptance_data)

    # 获取
    response = client.get("/api/small-box/TESTACCEPT/acceptance")
    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 1

def test_update_small_box_not_found(client: TestClient):
    """测试更新不存在的小箱"""
    update_data = {
        "envelope_count": 10,
    }
    response = client.put("/api/small-box/NOTEXIST", json=update_data)
    assert response.status_code == 404

def test_get_small_box_status_not_found(client: TestClient):
    """测试获取不存在小箱的状态"""
    response = client.get("/api/small-box/NOTEXIST/status")
    assert response.status_code == 404

def test_get_small_box_relations(client: TestClient):
    """测试获取小箱关联关系"""
    # 先创建两个小箱
    small_box_data1 = {
        "small_box_no": "CHILD001",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data1)
    small_box_data2 = {
        "small_box_no": "PARENT001",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data2)

    # 关系已经在 crud 测试中创建，但这里验证 API
    response = client.get("/api/small-box/CHILD001/relations")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)

def test_get_small_box_process(client: TestClient):
    """测试获取小箱工序数据"""
    from datetime import datetime
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTPROCESS",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    # 创建工序
    process_data = {
        "small_box_no": "TESTPROCESS",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": datetime.now().isoformat(),
    }
    client.post("/api/process/start", json=process_data)

    # 获取
    response = client.get("/api/small-box/TESTPROCESS/process")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) >= 1
