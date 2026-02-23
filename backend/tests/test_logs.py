"""Tests for audit log endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_create_log(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test creating an audit log"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Create log
    log_data = {
        "action": "read:file",
        "resource": "document.txt",
        "context": {"user_id": "usr_123"},
        "allowed": True,
        "result": "success",
        "metadata": {"bytes_read": 1024}
    }
    response = client.post("/logs", json=log_data, headers={"X-Agent-Key": api_key})
    assert response.status_code == 201

    data = response.json()
    assert "log_id" in data
    assert data["action"] == log_data["action"]
    assert data["resource"] == log_data["resource"]
    assert data["allowed"] == log_data["allowed"]


def test_create_log_requires_agent_auth(client: TestClient):
    """Test that creating a log requires agent authentication"""
    log_data = {
        "action": "read:file",
        "resource": "document.txt",
        "allowed": True,
        "result": "success"
    }
    response = client.post("/logs", json=log_data)
    assert response.status_code == 401


def test_query_logs_as_agent(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test querying logs as an agent (should only see own logs)"""
    # Create agent and submit logs
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Submit multiple logs
    for i in range(3):
        log_data = {
            "action": f"read:file{i}",
            "resource": f"document{i}.txt",
            "allowed": True,
            "result": "success"
        }
        client.post("/logs", json=log_data, headers={"X-Agent-Key": api_key})

    # Query logs
    response = client.get("/logs", headers={"X-Agent-Key": api_key})
    assert response.status_code == 200

    logs = response.json()
    assert len(logs) == 3


def test_query_logs_as_admin(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test querying logs as admin (can see all logs)"""
    # Create two agents
    agent1_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent1_key = agent1_response.json()["api_key"]

    agent2_data = {**sample_agent_data, "name": "test-agent-2"}
    agent2_response = client.post("/agents", json=agent2_data, headers=admin_headers)
    agent2_key = agent2_response.json()["api_key"]

    # Submit logs from both agents
    log_data = {"action": "test:action", "allowed": True, "result": "success"}
    client.post("/logs", json=log_data, headers={"X-Agent-Key": agent1_key})
    client.post("/logs", json=log_data, headers={"X-Agent-Key": agent2_key})

    # Admin queries all logs
    response = client.get("/logs", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_query_logs_filter_by_action(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test filtering logs by action"""
    # Create agent and submit logs
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Submit different actions
    client.post("/logs", json={"action": "read:file", "allowed": True, "result": "success"}, headers={"X-Agent-Key": api_key})
    client.post("/logs", json={"action": "write:file", "allowed": True, "result": "success"}, headers={"X-Agent-Key": api_key})
    client.post("/logs", json={"action": "read:file", "allowed": True, "result": "success"}, headers={"X-Agent-Key": api_key})

    # Filter by action
    response = client.get("/logs?action=read:file", headers={"X-Agent-Key": api_key})
    assert response.status_code == 200

    logs = response.json()
    assert len(logs) == 2
    assert all(log["action"] == "read:file" for log in logs)


def test_query_logs_filter_by_allowed(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test filtering logs by allowed status"""
    # Create agent and submit logs
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Submit logs with different allowed status
    client.post("/logs", json={"action": "test:action", "allowed": True, "result": "success"}, headers={"X-Agent-Key": api_key})
    client.post("/logs", json={"action": "test:action", "allowed": False, "result": "error"}, headers={"X-Agent-Key": api_key})

    # Filter by allowed=false
    response = client.get("/logs?allowed=false", headers={"X-Agent-Key": api_key})
    assert response.status_code == 200

    logs = response.json()
    assert all(log["allowed"] is False for log in logs)


def test_query_logs_pagination(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test log query pagination"""
    # Create agent and submit logs
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Submit multiple logs
    for i in range(10):
        log_data = {"action": f"test:action{i}", "allowed": True, "result": "success"}
        client.post("/logs", json=log_data, headers={"X-Agent-Key": api_key})

    # Test pagination
    response = client.get("/logs?limit=5&offset=0", headers={"X-Agent-Key": api_key})
    assert response.status_code == 200
    assert len(response.json()) == 5

    response = client.get("/logs?limit=5&offset=5", headers={"X-Agent-Key": api_key})
    assert response.status_code == 200
    assert len(response.json()) == 5
