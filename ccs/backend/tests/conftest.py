"""
测试配置
使用 SQLite 临时文件数据库进行测试
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 先导入模型确保它们被注册到 Base.metadata
from app.models import SmallBoxInfo, AcceptanceData, ProcessManagement, SmallBoxRelation, BoxStatus
from app.database import Base, get_db
from main import app

# 使用临时文件数据库 - 内存数据库在多连接情况下会丢失表
temp_file = tempfile.NamedTemporaryFile(delete=False)
temp_file.close()
SQLALCHEMY_DATABASE_URL = f"sqlite:///{temp_file.name}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_test_db():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)

def drop_test_db():
    """删除所有表"""
    Base.metadata.drop_all(bind=engine)
    # 在 Windows 上，SQLite 可能仍持有文件锁，无法立即删除
    try:
        os.unlink(temp_file.name)
    except (PermissionError, OSError):
        pass

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    init_test_db()
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        drop_test_db()

@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    # 覆盖 get_db 依赖
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
