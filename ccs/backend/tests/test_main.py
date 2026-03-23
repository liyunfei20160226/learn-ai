"""
测试主入口
"""

from fastapi.testclient import TestClient

def test_root(client: TestClient):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome" in data["message"]
    assert data["docs"] == "/docs"

def test_health_check(client: TestClient):
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
