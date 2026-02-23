"""Pytest configuration and fixtures"""
import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create test client with database session override"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers() -> dict:
    """Admin authentication headers"""
    return {"X-Admin-Key": os.getenv("ADMIN_API_KEY", "admin-secret-key-change-in-production")}


@pytest.fixture
def sample_agent_data() -> dict:
    """Sample agent data for tests"""
    return {
        "name": "test-agent",
        "owner_team": "engineering",
        "environment": "dev"
    }


@pytest.fixture
def sample_policy_data() -> dict:
    """Sample policy data for tests"""
    return {
        "allow": [
            {"action": "read:file", "resource": "*.txt"},
            {"action": "call:api", "resource": "api.internal.com/*"}
        ],
        "deny": [
            {"action": "delete:*", "resource": "*"}
        ]
    }
