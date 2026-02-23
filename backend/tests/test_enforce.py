"""Tests for enforcement endpoint"""
import pytest
from fastapi.testclient import TestClient

from app.api.enforce import normalize_action


def test_enforce_allowed(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement when action is allowed"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy
    policy = {
        "allow": [{"action": "read:file", "resource": "*.txt"}],
        "deny": []
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test enforcement
    response = client.post(
        "/enforce",
        json={"action": "read:file", "resource": "document.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is True
    assert "Allowed by rule" in data["reason"]


def test_enforce_denied_by_deny_rule(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement when action is denied by deny rule"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy with deny rule
    policy = {
        "allow": [{"action": "delete:*", "resource": "*"}],
        "deny": [{"action": "delete:*", "resource": "important.txt"}]
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test enforcement - should be denied (deny takes precedence)
    response = client.post(
        "/enforce",
        json={"action": "delete:file", "resource": "important.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert "Denied by rule" in data["reason"]


def test_enforce_denied_no_matching_rule(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement when no rules match (default deny)"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy
    policy = {
        "allow": [{"action": "read:file", "resource": "*.txt"}],
        "deny": []
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test enforcement with non-matching action
    response = client.post(
        "/enforce",
        json={"action": "write:file", "resource": "document.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert "default deny" in data["reason"].lower()


def test_enforce_no_policy(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement when no policy exists (default deny)"""
    # Create agent without policy
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    api_key = create_response.json()["api_key"]

    # Test enforcement
    response = client.post(
        "/enforce",
        json={"action": "read:file", "resource": "document.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert "No policy defined" in data["reason"]


def test_enforce_requires_agent_auth(client: TestClient):
    """Test that enforcement requires agent authentication"""
    response = client.post(
        "/enforce",
        json={"action": "read:file", "resource": "document.txt"}
    )
    assert response.status_code == 401


def test_enforce_wildcard_action(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement with wildcard actions"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy with wildcard
    policy = {
        "allow": [{"action": "read:*", "resource": "*"}],
        "deny": []
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test various read actions
    for action in ["read:file", "read:database", "read:api"]:
        response = client.post(
            "/enforce",
            json={"action": action, "resource": "test"},
            headers={"X-Agent-Key": api_key}
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True


def test_enforce_wildcard_resource(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement with wildcard resources"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy with resource wildcard
    policy = {
        "allow": [{"action": "read:file", "resource": "s3://bucket/*"}],
        "deny": []
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test matching resource
    response = client.post(
        "/enforce",
        json={"action": "read:file", "resource": "s3://bucket/file.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is True

    # Test non-matching resource
    response = client.post(
        "/enforce",
        json={"action": "read:file", "resource": "s3://other-bucket/file.txt"},
        headers={"X-Agent-Key": api_key}
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is False


# ===== Action Normalization Tests =====


def test_normalize_action_standard_format():
    """Test normalization of standard verb:noun format"""
    assert normalize_action("read:file") == "read:file"
    assert normalize_action("write:file") == "write:file"
    assert normalize_action("delete:database") == "delete:database"
    assert normalize_action("send:email") == "send:email"


def test_normalize_action_spaces():
    """Test normalization of space-separated format"""
    assert normalize_action("read file") == "read:file"
    assert normalize_action("write file") == "write:file"
    assert normalize_action("delete database") == "delete:database"
    assert normalize_action("send email") == "send:email"
    assert normalize_action("query database") == "query:database"


def test_normalize_action_hyphens():
    """Test normalization of hyphen-separated format"""
    assert normalize_action("read-file") == "read:file"
    assert normalize_action("write-file") == "write:file"
    assert normalize_action("delete-database") == "delete:database"
    assert normalize_action("send-email") == "send:email"


def test_normalize_action_underscores():
    """Test normalization of underscore-separated format"""
    assert normalize_action("read_file") == "read:file"
    assert normalize_action("write_file") == "write:file"
    assert normalize_action("delete_database") == "delete:database"
    assert normalize_action("send_email") == "send:email"


def test_normalize_action_camel_case():
    """Test normalization of camelCase format"""
    assert normalize_action("readFile") == "read:file"
    assert normalize_action("writeFile") == "write:file"
    assert normalize_action("deleteDatabase") == "delete:database"
    assert normalize_action("sendEmail") == "send:email"


def test_normalize_action_natural_language():
    """Test normalization of natural language format"""
    assert normalize_action("Read File") == "read:file"
    assert normalize_action("Write File") == "write:file"
    assert normalize_action("DELETE DATABASE") == "delete:database"
    assert normalize_action("Send Email") == "send:email"


def test_normalize_action_mixed_formats():
    """Test normalization of mixed formats"""
    assert normalize_action("Read-File") == "read:file"
    assert normalize_action("WRITE_FILE") == "write:file"
    assert normalize_action("Delete Database") == "delete:database"
    assert normalize_action("send-Email") == "send:email"


def test_normalize_action_single_word():
    """Test normalization of single-word actions (for wildcards)"""
    assert normalize_action("read") == "read"
    assert normalize_action("write") == "write"
    assert normalize_action("delete") == "delete"
    assert normalize_action("*") == "*"


def test_normalize_action_wildcards():
    """Test normalization preserves wildcards"""
    assert normalize_action("delete *") == "delete:*"
    assert normalize_action("delete:*") == "delete:*"
    assert normalize_action("read *") == "read:*"
    assert normalize_action("*:file") == "*:file"


def test_normalize_action_extra_whitespace():
    """Test normalization handles extra whitespace"""
    assert normalize_action("  read file  ") == "read:file"
    assert normalize_action("read  file") == "read:file"
    assert normalize_action("\tread\tfile\t") == "read:file"


def test_normalize_action_multi_word():
    """Test normalization with more than two words (uses first two)"""
    assert normalize_action("read file system") == "read:file"
    assert normalize_action("send email notification") == "send:email"
    assert normalize_action("delete database records") == "delete:database"


def test_enforce_with_natural_actions(client: TestClient, admin_headers: dict, sample_agent_data: dict):
    """Test enforcement works with natural action formats"""
    # Create agent
    create_response = client.post("/agents", json=sample_agent_data, headers=admin_headers)
    agent_id = create_response.json()["agent_id"]
    api_key = create_response.json()["api_key"]

    # Set policy with standard format
    policy = {
        "allow": [{"action": "read:file", "resource": "*.txt"}],
        "deny": []
    }
    client.put(f"/agents/{agent_id}/policy", json=policy, headers=admin_headers)

    # Test with various natural formats
    natural_formats = [
        "read file",
        "Read File",
        "read-file",
        "read_file",
        "readFile",
        "READ FILE",
        "read:file"  # standard format
    ]

    for action_format in natural_formats:
        response = client.post(
            "/enforce",
            json={"action": action_format, "resource": "document.txt"},
            headers={"X-Agent-Key": api_key}
        )
        assert response.status_code == 200, f"Failed for format: {action_format}"
        data = response.json()
        assert data["allowed"] is True, f"Should be allowed for format: {action_format}"
        assert "Allowed by rule" in data["reason"]
