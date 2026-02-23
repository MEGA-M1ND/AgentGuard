"""Tests for policy endpoints"""
import pytest
from fastapi.testclient import TestClient


def test_set_policy(client: TestClient, admin_headers: dict, sample_agent_data: dict, sample_policy_data: dict):
    """Test setting a policy for an agent"""
    # Create an agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]

    # Set policy
    response = client.put(f"/agents/{agent_id}/policy", json=sample_policy_data, headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["agent_id"] == agent_id
    assert len(data["allow"]) == 2
    assert len(data["deny"]) == 1


def test_set_policy_requires_admin(client: TestClient, sample_agent_data: dict, sample_policy_data: dict, admin_headers: dict):
    """Test that setting policy requires admin auth"""
    # Create an agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]

    # Try to set policy without auth
    response = client.put(f"/agents/{agent_id}/policy", json=sample_policy_data)
    assert response.status_code == 401


def test_set_policy_for_nonexistent_agent(client: TestClient, admin_headers: dict, sample_policy_data: dict):
    """Test setting policy for non-existent agent"""
    response = client.put("/agents/agt_notfound/policy", json=sample_policy_data, headers=admin_headers)
    assert response.status_code == 404


def test_get_policy(client: TestClient, admin_headers: dict, sample_agent_data: dict, sample_policy_data: dict):
    """Test getting a policy"""
    # Create agent and set policy
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    client.put(f"/agents/{agent_id}/policy", json=sample_policy_data, headers=admin_headers)

    # Get policy
    response = client.get(f"/agents/{agent_id}/policy", headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["agent_id"] == agent_id
    assert len(data["allow"]) == 2
    assert len(data["deny"]) == 1


def test_get_policy_not_found(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test getting policy when none exists"""
    # Create agent without policy
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]

    # Try to get policy
    response = client.get(f"/agents/{agent_id}/policy", headers=admin_headers)
    assert response.status_code == 404


def test_update_policy(client: TestClient, admin_headers: dict, sample_agent_data: dict, sample_policy_data: dict):
    """Test updating an existing policy"""
    # Create agent and set policy
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    client.put(f"/agents/{agent_id}/policy", json=sample_policy_data, headers=admin_headers)

    # Update policy
    new_policy = {
        "allow": [{"action": "write:file", "resource": "*.txt"}],
        "deny": []
    }
    response = client.put(f"/agents/{agent_id}/policy", json=new_policy, headers=admin_headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data["allow"]) == 1
    assert len(data["deny"]) == 0
    assert data["allow"][0]["action"] == "write:file"
