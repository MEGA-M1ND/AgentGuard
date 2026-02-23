"""
Demo Data Seeder for AgentGuard

Creates realistic demo data including:
- 3 pre-configured agents with different roles
- Policies for each agent
- 50+ audit log entries with realistic scenarios

Run this script to populate the database with demo data for showcasing.
"""
import random
import requests
from datetime import datetime, timedelta
from typing import Dict, List

# API Configuration
API_URL = "http://localhost:8000"
ADMIN_API_KEY = "admin-secret-key"

# Demo Agents Configuration
DEMO_AGENTS = [
    {
        "name": "CustomerSupportBot",
        "owner_team": "Support Team",
        "environment": "production",
        "description": "Handles customer inquiries and support tickets"
    },
    {
        "name": "DataAnalyzer",
        "owner_team": "Analytics Team",
        "environment": "production",
        "description": "Analyzes customer data and generates reports"
    },
    {
        "name": "ContentModerator",
        "owner_team": "Moderation Team",
        "environment": "production",
        "description": "Reviews and moderates user-generated content"
    }
]

# Policies for each agent
POLICIES = {
    "CustomerSupportBot": {
        "allow": [
            {"action": "read:ticket", "resource": "*"},
            {"action": "read:customer", "resource": "*"},
            {"action": "send:email", "resource": "support/*"},
            {"action": "update:ticket", "resource": "*"},
            {"action": "create:response", "resource": "*"}
        ],
        "deny": [
            {"action": "delete:*", "resource": "*"},
            {"action": "read:payment", "resource": "*"},
            {"action": "update:customer", "resource": "*"}
        ]
    },
    "DataAnalyzer": {
        "allow": [
            {"action": "read:customer", "resource": "*"},
            {"action": "read:analytics", "resource": "*"},
            {"action": "query:database", "resource": "analytics/*"},
            {"action": "generate:report", "resource": "*"},
            {"action": "export:data", "resource": "reports/*"}
        ],
        "deny": [
            {"action": "delete:*", "resource": "*"},
            {"action": "update:*", "resource": "*"},
            {"action": "read:payment", "resource": "*"}
        ]
    },
    "ContentModerator": {
        "allow": [
            {"action": "read:content", "resource": "*"},
            {"action": "review:content", "resource": "*"},
            {"action": "flag:content", "resource": "*"},
            {"action": "delete:content", "resource": "user-generated/*"},
            {"action": "ban:user", "resource": "*"}
        ],
        "deny": [
            {"action": "delete:content", "resource": "official/*"},
            {"action": "read:payment", "resource": "*"},
            {"action": "access:admin", "resource": "*"}
        ]
    }
}

# Sample actions for log generation
LOG_SCENARIOS = {
    "CustomerSupportBot": [
        {"action": "read:ticket", "resource": "ticket-12345", "allowed": True, "result": "success"},
        {"action": "read:customer", "resource": "customer-abc123", "allowed": True, "result": "success"},
        {"action": "send:email", "resource": "support/notification", "allowed": True, "result": "success"},
        {"action": "update:ticket", "resource": "ticket-12345", "allowed": True, "result": "success"},
        {"action": "create:response", "resource": "ticket-67890", "allowed": True, "result": "success"},
        {"action": "delete:ticket", "resource": "ticket-12345", "allowed": False, "result": "denied"},
        {"action": "read:payment", "resource": "payment-info", "allowed": False, "result": "denied"},
        {"action": "update:customer", "resource": "customer-xyz", "allowed": False, "result": "denied"},
        {"action": "read:ticket", "resource": "ticket-99999", "allowed": True, "result": "success"},
        {"action": "send:email", "resource": "support/alert", "allowed": True, "result": "success"},
    ],
    "DataAnalyzer": [
        {"action": "read:customer", "resource": "customer-list", "allowed": True, "result": "success"},
        {"action": "read:analytics", "resource": "dashboard-metrics", "allowed": True, "result": "success"},
        {"action": "query:database", "resource": "analytics/sales", "allowed": True, "result": "success"},
        {"action": "generate:report", "resource": "monthly-report", "allowed": True, "result": "success"},
        {"action": "export:data", "resource": "reports/Q1-2025", "allowed": True, "result": "success"},
        {"action": "delete:customer", "resource": "customer-123", "allowed": False, "result": "denied"},
        {"action": "update:analytics", "resource": "dashboard", "allowed": False, "result": "denied"},
        {"action": "read:payment", "resource": "payment-data", "allowed": False, "result": "denied"},
        {"action": "query:database", "resource": "analytics/users", "allowed": True, "result": "success"},
        {"action": "generate:report", "resource": "weekly-summary", "allowed": True, "result": "success"},
    ],
    "ContentModerator": [
        {"action": "read:content", "resource": "post-12345", "allowed": True, "result": "success"},
        {"action": "review:content", "resource": "post-67890", "allowed": True, "result": "success"},
        {"action": "flag:content", "resource": "comment-abc", "allowed": True, "result": "success"},
        {"action": "delete:content", "resource": "user-generated/spam-post", "allowed": True, "result": "success"},
        {"action": "ban:user", "resource": "user-spammer", "allowed": True, "result": "success"},
        {"action": "delete:content", "resource": "official/announcement", "allowed": False, "result": "denied"},
        {"action": "read:payment", "resource": "user-payment", "allowed": False, "result": "denied"},
        {"action": "access:admin", "resource": "admin-panel", "allowed": False, "result": "denied"},
        {"action": "flag:content", "resource": "post-suspicious", "allowed": True, "result": "success"},
        {"action": "review:content", "resource": "comment-xyz", "allowed": True, "result": "success"},
    ]
}


def create_agent(agent_data: Dict) -> Dict:
    """Create a new agent"""
    response = requests.post(
        f"{API_URL}/agents",
        json=agent_data,
        headers={"X-ADMIN-KEY": ADMIN_API_KEY}
    )
    response.raise_for_status()
    return response.json()


def set_policy(agent_id: str, policy: Dict):
    """Set policy for an agent"""
    response = requests.put(
        f"{API_URL}/agents/{agent_id}/policy",
        json=policy,
        headers={"X-ADMIN-KEY": ADMIN_API_KEY}
    )
    response.raise_for_status()
    return response.json()


def create_log(agent_id: str, agent_api_key: str, log_data: Dict):
    """Create an audit log entry"""
    response = requests.post(
        f"{API_URL}/logs",
        json=log_data,
        headers={"X-Agent-Key": agent_api_key}
    )
    response.raise_for_status()
    return response.json()


def generate_timestamp(hours_ago: int, minutes_offset: int = 0) -> str:
    """Generate a timestamp N hours ago with optional minute offset"""
    timestamp = datetime.utcnow() - timedelta(hours=hours_ago, minutes=minutes_offset)
    return timestamp.isoformat() + "Z"


def seed_demo_data():
    """Main function to seed all demo data"""
    print("AgentGuard Demo Data Seeder")
    print("=" * 50)

    created_agents = []

    # Step 1: Create agents
    print("\nCreating demo agents...")
    for agent_config in DEMO_AGENTS:
        try:
            agent = create_agent(agent_config)
            created_agents.append(agent)
            print(f"[+] Created agent: {agent['name']} (ID: {agent['agent_id'][:12]}...)")
            print(f"    API Key: {agent['api_key'][:20]}...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                print(f"[!] Agent {agent_config['name']} already exists, skipping...")
                # Fetch existing agent
                response = requests.get(
                    f"{API_URL}/agents",
                    headers={"X-ADMIN-KEY": ADMIN_API_KEY}
                )
                agents = response.json()
                existing = next((a for a in agents if a['name'] == agent_config['name']), None)
                if existing:
                    print(f"    Using existing agent ID: {existing['agent_id'][:12]}...")
                    # Note: We can't get the API key for existing agents, so we'll skip log creation for them
            else:
                print(f"[-] Error creating agent: {e}")

    # Step 2: Set policies
    print("\nSetting policies for agents...")
    for agent in created_agents:
        agent_name = agent['name']
        if agent_name in POLICIES:
            try:
                set_policy(agent['agent_id'], POLICIES[agent_name])
                print(f"[+] Set policy for {agent_name}")
                print(f"    Allow rules: {len(POLICIES[agent_name]['allow'])}")
                print(f"    Deny rules: {len(POLICIES[agent_name]['deny'])}")
            except Exception as e:
                print(f"[-] Error setting policy for {agent_name}: {e}")

    # Step 3: Generate audit logs
    print("\nGenerating audit log entries...")
    total_logs = 0

    for agent in created_agents:
        agent_name = agent['name']
        agent_id = agent['agent_id']
        agent_api_key = agent['api_key']

        if agent_name not in LOG_SCENARIOS:
            continue

        scenarios = LOG_SCENARIOS[agent_name]

        # Generate logs spread over last 24 hours
        hours_range = 24
        logs_per_hour = len(scenarios)

        for hour in range(hours_range):
            # Pick a random scenario for this hour
            scenario = random.choice(scenarios)

            # Add some random minute offset for variety
            minute_offset = random.randint(0, 59)

            log_data = {
                "action": scenario["action"],
                "resource": scenario["resource"],
                "allowed": scenario["allowed"],
                "result": scenario["result"],
                "context": {
                    "source": "demo-seeder",
                    "hour": hour,
                    "agent_name": agent_name
                },
                "metadata": {
                    "demo": True,
                    "timestamp_offset_hours": hour
                }
            }

            try:
                create_log(agent_id, agent_api_key, log_data)
                total_logs += 1
            except Exception as e:
                print(f"[!] Error creating log for {agent_name}: {e}")

        print(f"[+] Generated {hours_range} logs for {agent_name}")

    # Summary
    print("\n" + "=" * 50)
    print("Demo data seeding complete!")
    print(f"Agents created: {len(created_agents)}")
    print(f"Policies set: {len(created_agents)}")
    print(f"Audit logs created: {total_logs}")
    print("\nYour AgentGuard dashboard is now ready for demo!")
    print(f"Dashboard: http://localhost:3000")
    print(f"Agents: {', '.join([a['name'] for a in created_agents])}")


if __name__ == "__main__":
    try:
        seed_demo_data()
    except Exception as e:
        print(f"\n[-] Error during seeding: {e}")
        print("Make sure the backend is running on http://localhost:8000")
