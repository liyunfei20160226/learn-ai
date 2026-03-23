"""
测试 工序管理 API 接口
"""

from datetime import datetime
from fastapi.testclient import TestClient

def test_get_process_not_found(client: TestClient):
    """测试获取不存在的工序"""
    now = datetime.now().isoformat()
    response = client.get(f"/api/process/TEST001/01/USER01/{now}")
    assert response.status_code == 404

def test_start_process(client: TestClient):
    """测试开始工序"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TEST001",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    now = datetime.now().isoformat()
    process_data = {
        "small_box_no": "TEST001",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
    }
    response = client.post("/api/process/start", json=process_data)
    assert response.status_code == 200
    result = response.json()
    assert result["small_box_no"] == "TEST001"
    assert result["process_div"] == "01"

def test_start_process_duplicate(client: TestClient):
    """测试重复开始工序应该报错"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDUP",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    now = datetime.now().isoformat()
    process_data = {
        "small_box_no": "TESTDUP",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
    }
    # 第一次
    client.post("/api/process/start", json=process_data)
    # 第二次应该失败
    response = client.post("/api/process/start", json=process_data)
    assert response.status_code == 400
    assert "已存在" in response.json()["detail"]

def test_end_process(client: TestClient):
    """测试结束工序"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTEND",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    now = datetime.now().isoformat()
    process_data = {
        "small_box_no": "TESTEND",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
    }
    response = client.post("/api/process/start", json=process_data)

    # 结束工序
    end_data = {
        "small_box_no": "TESTEND",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
        "end_datetime": datetime.now().isoformat(),
    }
    response = client.put("/api/process/end", json=end_data)
    assert response.status_code == 200
    result = response.json()
    assert result["end_datetime"] is not None
    assert result["modify_date"] is not None

def test_list_process_by_small_box(client: TestClient):
    """测试按小箱获取工序列表"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTLIST",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    for i in range(2):
        now = datetime.now().isoformat()
        process_data = {
            "small_box_no": "TESTLIST",
            "process_div": "01",
            "personal_code": f"USER{i}",
            "start_datetime": now,
        }
        client.post("/api/process/start", json=process_data)

    response = client.get("/api/process/by-small-box/TESTLIST")
    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 2

def test_delete_process(client: TestClient):
    """测试删除工序"""
    # 先创建小箱
    small_box_data = {
        "small_box_no": "TESTDEL",
        "system_div": "01",
        "register_date": "2024-01-01",
    }
    client.post("/api/small-box/", json=small_box_data)

    now = datetime.now().isoformat()
    process_data = {
        "small_box_no": "TESTDEL",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
    }
    client.post("/api/process/start", json=process_data)

    response = client.delete(f"/api/process/TESTDEL/01/USER01/{now}")
    assert response.status_code == 200
    result = response.json()
    assert "删除成功" in result["message"]

def test_end_process_not_found(client: TestClient):
    """测试结束不存在的工序"""
    now = datetime.now().isoformat()
    end_data = {
        "small_box_no": "NOTEXIST",
        "process_div": "01",
        "personal_code": "USER01",
        "start_datetime": now,
        "end_datetime": datetime.now().isoformat(),
    }
    response = client.put("/api/process/end", json=end_data)
    assert response.status_code == 404

def test_delete_process_not_found(client: TestClient):
    """测试删除不存在的工序"""
    now = datetime.now().isoformat()
    response = client.delete(f"/api/process/NOTEXIST/01/USER01/{now}")
    assert response.status_code == 404
