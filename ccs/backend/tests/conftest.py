"""
pytest fixtures for testing
"""

import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
# Import all models to ensure they're registered in Base.metadata
import app.models.small_box_info  # noqa: F401
from main import app

# Use temporary file SQLite for testing (avoids in-memory connection issues)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    # Create a temporary file for SQLite
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name

    engine = create_engine(f"sqlite:///{temp_db_path}", echo=False, connect_args={"check_same_thread": False})
    # Create all tables
    Base.metadata.create_all(engine)
    # Debug: list tables
    from sqlalchemy.inspection import inspect
    inspector = inspect(engine)
    print(f"[DEBUG] Tables in SQLite: {inspector.get_table_names()}")

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
        # Clean up temporary file
        os.unlink(temp_db_path)


@pytest.fixture
async def client(db):
    """Create an async test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
