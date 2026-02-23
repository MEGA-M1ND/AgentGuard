"""AgentGuard quickstart example

This script demonstrates the complete flow of:
1. Creating an agent (admin)
2. Setting a policy (admin)
3. Testing enforcement (agent)
4. Submitting audit logs (agent)
5. Querying logs (admin/agent)
"""
import os
import time

from agentguard import AgentGuardClient

# Configuration
BACKEND_URL = os.getenv("AGENTGUARD_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key-change-in-production")


def main():
    print("=" * 60)
    print("AgentGuard Quickstart Demo")
    print("=" * 60)
    print()

    # Step 1: Create admin client
    print("1. Creating admin client...")
    admin = AgentGuardClient(base_url=BACKEND_URL, admin_key=ADMIN_KEY)
    print("   ✓ Admin client created")
    print()

    # Step 2: Create an agent
    print("2. Creating agent...")
    agent = admin.create_agent(
        name="demo-agent",
        owner_team="engineering",
        environment="dev"
    )
    agent_id = agent["agent_id"]
    api_key = agent["api_key"]
    print(f"   ✓ Agent created: {agent_id}")
    print(f"   ✓ API Key: {api_key[:20]}...")
    print()

    # Step 3: Set policy
    print("3. Setting policy...")
    policy = admin.set_policy(
        agent_id=agent_id,
        allow=[
            {"action": "read:file", "resource": "*.txt"},
            {"action": "read:file", "resource": "*.pdf"},
            {"action": "call:api", "resource": "api.internal.com/*"}
        ],
        deny=[
            {"action": "delete:*", "resource": "*"},
            {"action": "write:file", "resource": "sensitive.txt"}
        ]
    )
    print(f"   ✓ Policy set with {len(policy['allow'])} allow rules and {len(policy['deny'])} deny rules")
    print()

    # Step 4: Create agent client
    print("4. Creating agent client...")
    client = AgentGuardClient(base_url=BACKEND_URL, agent_key=api_key)
    print("   ✓ Agent client created")
    print()

    # Step 5: Test enforcement
    print("5. Testing enforcement...")
    test_cases = [
        ("read:file", "document.txt", True),
        ("read:file", "report.pdf", True),
        ("write:file", "data.txt", False),
        ("delete:file", "old.txt", False),
        ("call:api", "api.internal.com/v1/users", True),
    ]

    for action, resource, expected_allowed in test_cases:
        result = client.enforce(action=action, resource=resource)
        status = "✓" if result["allowed"] == expected_allowed else "✗"
        allowed_str = "ALLOWED" if result["allowed"] else "DENIED"
        print(f"   {status} {action} on {resource}: {allowed_str}")
        print(f"      Reason: {result['reason']}")

    print()

    # Step 6: Submit audit logs
    print("6. Submitting audit logs...")
    log_entries = [
        {
            "action": "read:file",
            "resource": "document.txt",
            "allowed": True,
            "result": "success",
            "metadata": {"bytes_read": 1024, "duration_ms": 45}
        },
        {
            "action": "read:file",
            "resource": "report.pdf",
            "allowed": True,
            "result": "success",
            "metadata": {"bytes_read": 2048, "duration_ms": 67}
        },
        {
            "action": "delete:file",
            "resource": "old.txt",
            "allowed": False,
            "result": "error",
            "metadata": {"error": "Permission denied"}
        }
    ]

    for log_entry in log_entries:
        log = client.log_action(**log_entry)
        print(f"   ✓ Log created: {log['log_id']}")

    print()

    # Step 7: Query logs
    print("7. Querying logs...")
    time.sleep(0.5)  # Brief pause to ensure logs are written

    # Query all logs for this agent
    logs = client.query_logs()
    print(f"   ✓ Found {len(logs)} total logs for this agent")

    # Query only allowed actions
    allowed_logs = client.query_logs(allowed=True)
    print(f"   ✓ Found {len(allowed_logs)} allowed actions")

    # Query only denied actions
    denied_logs = client.query_logs(allowed=False)
    print(f"   ✓ Found {len(denied_logs)} denied actions")

    print()

    # Step 8: Display sample log
    print("8. Sample log entry:")
    if logs:
        sample = logs[0]
        print(f"   Log ID: {sample['log_id']}")
        print(f"   Agent ID: {sample['agent_id']}")
        print(f"   Action: {sample['action']}")
        print(f"   Resource: {sample['resource']}")
        print(f"   Allowed: {sample['allowed']}")
        print(f"   Result: {sample['result']}")
        print(f"   Timestamp: {sample['timestamp']}")

    print()

    # Step 9: Cleanup
    print("9. Cleanup (optional - delete agent)...")
    print("   Skipping cleanup in demo. To delete agent, run:")
    print(f"   admin.delete_agent('{agent_id}')")
    print()

    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("- View logs in the UI dashboard at http://localhost:3000")
    print("- Try different policy rules")
    print("- Integrate with your AI agents")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
