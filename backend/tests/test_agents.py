"""Tests for agent endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_create_agent(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test creating an agent"""
    response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    assert response.status_code == 201

    data = response.json()
    assert "agent_id" in data
    assert data["agent_id"].startswith("agt_")
    assert "api_key" in data
    assert data["api_key"].startswith("agk_")
    assert data["name"] == sample_agent_data["name"]
    assert data["owner_team"] == sample_agent_data["owner_team"]
    assert data["environment"] == sample_agent_data["environment"]


def test_create_agent_requires_admin(client: TestClient, sample_agent_data: dict):
    """Test that creating an agent requires admin auth"""
    response = client.post("/agents", json=sample_agent_data)
    assert response.status_code == 401


def test_list_agents(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test listing agents"""
    # Create an agent first
    client.post("/agents", json=sample_agent_data, headers=admin_headers)

    # List agents
    response = client.get("/agents", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_agent(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test getting a specific agent"""
    # Create an agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]

    # Get agent
    response = client.get(f"/agents/{agent_id}", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["agent_id"] == agent_id
    assert "api_key" not in data  # API key should not be returned


def test_get_agent_not_found(client: TestClient, admin_headers: dict):
    """Test getting a non-existent agent"""
    response = client.get("/agents/agt_notfound", headers=admin_headers)
    assert response.status_code == 404


def test_delete_agent(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test deleting an agent"""
    # Create an agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]

    # Delete agent
    response = client.delete(f"/agents/{agent_id}", headers=admin_headers)
    assert response.status_code == 204

    # Verify agent is inactive
    get_response = client.get(f"/agents/{agent_id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


def test_filter_agents_by_environment(client: TestClient, admin_headers: dict):
    """Test filtering agents by environment"""
    # Create agents in different environments
    client.post("/agents", json={"name": "dev-agent", "owner_team": "team1", "environment": "dev"}, headers=admin_headers)
    client.post("/agents", json={"name": "prod-agent", "owner_team": "team1", "environment": "prod"}, headers=admin_headers)

    # Filter by dev
    response = client.get("/agents?environment=dev", headers=admin_headers)
    assert response.status_code == 200
    agents = response.json()
    assert all(agent["environment"] == "dev" for agent in agents)
