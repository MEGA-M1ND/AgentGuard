"""
Demo seed script — populates realistic data for a LinkedIn live demo.

Run AFTER the server is started:
    python demo_seed.py

Creates:
  - 3 agents across 2 teams (payments, data-science)
  - Policies with conditions on each agent
  - Team-level deny policy for payments
  - 2 admin users (auditor + approver)
  - ~20 audit log entries with a valid chain
  - 1 pending approval request
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
ADMIN_KEY = "admin123"  # matches .env ADMIN_API_KEY


def call(method, path, body=None, key_header=("X-Admin-Key", ADMIN_KEY)):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header(key_header[0], key_header[1])
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR {e.code} on {method} {path}: {body[:200]}")
        return None


def main():
    print("\n🌱 Seeding demo data for AgentGuard...\n")

    # ── 1. Create agents ──────────────────────────────────────────────────────
    print("Creating agents...")

    pa = call("POST", "/agents", {
        "name": "Payment Processor",
        "owner_team": "payments",
        "environment": "production"
    })
    if not pa:
        print("  ❌ Could not create agent. Is the server running at http://localhost:8000?")
        sys.exit(1)
    payment_agent_id = pa["agent_id"]
    payment_agent_key = pa["api_key"]
    print(f"  ✓ Payment Processor  {payment_agent_id}")

    ra = call("POST", "/agents", {
        "name": "Risk Analyser",
        "owner_team": "payments",
        "environment": "staging"
    })
    risk_agent_id = ra["agent_id"]
    risk_agent_key = ra["api_key"]
    print(f"  ✓ Risk Analyser      {risk_agent_id}")

    da = call("POST", "/agents", {
        "name": "Data Pipeline",
        "owner_team": "data-science",
        "environment": "development"
    })
    data_agent_id = da["agent_id"]
    data_agent_key = da["api_key"]
    print(f"  ✓ Data Pipeline      {data_agent_id}")

    # ── 2. Set agent policies ─────────────────────────────────────────────────
    print("\nSetting policies...")

    call("PUT", f"/agents/{payment_agent_id}/policy", {
        "allow_rules": [
            {"action": "read:*", "resource": "*"},
            {
                "action": "write:transaction",
                "resource": "payments/*",
                "conditions": {
                    "env": ["production"],
                    "time_range": {"start": "08:00", "end": "20:00", "tz": "UTC"},
                    "day_of_week": ["Mon", "Tue", "Wed", "Thu", "Fri"]
                }
            }
        ],
        "deny_rules": [
            {"action": "delete:*", "resource": "*"}
        ],
        "require_approval_rules": [
            {"action": "export:*", "resource": "payments/*"}
        ]
    })
    print(f"  ✓ Payment Processor policy  (conditional write + approval on export)")

    call("PUT", f"/agents/{risk_agent_id}/policy", {
        "allow_rules": [
            {"action": "read:*", "resource": "*"},
            {"action": "query:model", "resource": "risk/*"},
            {"action": "write:report", "resource": "risk/*"}
        ],
        "deny_rules": [],
        "require_approval_rules": []
    })
    print(f"  ✓ Risk Analyser policy  (read + query model + write report)")

    call("PUT", f"/agents/{data_agent_id}/policy", {
        "allow_rules": [
            {"action": "read:*", "resource": "*"},
            {"action": "write:*", "resource": "datasets/*"},
            {"action": "execute:pipeline", "resource": "*",
             "conditions": {"env": ["development", "staging"]}}
        ],
        "deny_rules": [
            {"action": "delete:*", "resource": "datasets/production*"}
        ],
        "require_approval_rules": []
    })
    print(f"  ✓ Data Pipeline policy  (env-gated pipeline execution)")

    # ── 3. Set team policy for payments ──────────────────────────────────────
    print("\nSetting team policy...")

    call("PUT", "/teams/payments/policy", {
        "deny_rules": [
            {"action": "delete:*", "resource": "production/*"},
            {"action": "export:pii", "resource": "*"}
        ],
        "allow_rules": [],
        "require_approval_rules": [
            {"action": "transfer:funds", "resource": "*"}
        ]
    })
    print("  ✓ payments team policy  (team-wide: deny delete+pii export, approval on fund transfer)")

    # ── 4. Create admin users ─────────────────────────────────────────────────
    print("\nCreating admin users...")

    auditor = call("POST", "/admin/users", {
        "name": "Alice Chen",
        "role": "auditor",
        "team": "payments"
    })
    print(f"  ✓ Alice Chen  (auditor, payments team)  key: {auditor['api_key'][:20]}...")

    approver = call("POST", "/admin/users", {
        "name": "Bob Sharma",
        "role": "approver",
        "team": None
    })
    print(f"  ✓ Bob Sharma  (approver, all teams)  key: {approver['api_key'][:20]}...")

    # Save keys for demo use
    with open("demo_keys.txt", "w") as f:
        f.write(f"PAYMENT_AGENT_ID={payment_agent_id}\n")
        f.write(f"PAYMENT_AGENT_KEY={payment_agent_key}\n")
        f.write(f"RISK_AGENT_ID={risk_agent_id}\n")
        f.write(f"RISK_AGENT_KEY={risk_agent_key}\n")
        f.write(f"DATA_AGENT_ID={data_agent_id}\n")
        f.write(f"DATA_AGENT_KEY={data_agent_key}\n")
        f.write(f"AUDITOR_KEY={auditor['api_key']}\n")
        f.write(f"APPROVER_KEY={approver['api_key']}\n")
    print("\n  📄 Keys saved to demo_keys.txt")

    # ── 5. Generate audit log entries ─────────────────────────────────────────
    print("\nGenerating audit log entries...")

    log_entries = [
        # Payment agent — mix of allowed and denied
        (payment_agent_key, "read:account", "payments/ACC-001", True),
        (payment_agent_key, "read:balance", "payments/ACC-001", True),
        (payment_agent_key, "write:transaction", "payments/TXN-9921", True),
        (payment_agent_key, "write:transaction", "payments/TXN-9922", True),
        (payment_agent_key, "delete:record", "payments/ACC-OLD", False),
        (payment_agent_key, "read:account", "payments/ACC-002", True),
        (payment_agent_key, "write:transaction", "payments/TXN-9923", True),
        (payment_agent_key, "export:pii", "payments/customer_data", False),  # team deny
        # Risk agent
        (risk_agent_key, "read:transaction", "risk/history", True),
        (risk_agent_key, "query:model", "risk/fraud-model-v2", True),
        (risk_agent_key, "query:model", "risk/fraud-model-v2", True),
        (risk_agent_key, "write:report", "risk/daily-fraud-report", True),
        (risk_agent_key, "delete:model", "risk/old-model", False),
        # Data pipeline
        (data_agent_key, "read:schema", "datasets/customers", True),
        (data_agent_key, "execute:pipeline", "etl/customer_pipeline", True),
        (data_agent_key, "write:dataset", "datasets/processed/output", True),
        (data_agent_key, "delete:dataset", "datasets/production/customers", False),
        (data_agent_key, "read:schema", "datasets/orders", True),
        (data_agent_key, "execute:pipeline", "etl/orders_pipeline", True),
    ]

    for agent_key, action, resource, allowed in log_entries:
        call("POST", "/logs",
             {"action": action, "resource": resource, "allowed": allowed,
              "result": "success" if allowed else "error"},
             key_header=("X-Agent-Key", agent_key))

    print(f"  ✓ {len(log_entries)} audit log entries created")

    # ── 6. Create a pending approval request ─────────────────────────────────
    print("\nCreating pending approval request...")

    # Trigger export:data to create an approval
    call("POST", "/enforce",
         {"action": "export:data", "resource": "payments/Q4-report"},
         key_header=("X-Agent-Key", payment_agent_key))
    print("  ✓ Pending approval: export:data → payments/Q4-report")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  Demo data ready!

Open the UI:     http://localhost:3000
API docs:        http://localhost:8000/docs

Agents:
  Payment Processor  ({payment_agent_id})  env=production
  Risk Analyser      ({risk_agent_id})  env=staging
  Data Pipeline      ({data_agent_id})  env=development

Admin users:
  Alice Chen  — auditor, scoped to payments team
  Bob Sharma  — approver, all teams

Pending approval: 1 (export:data on payments/Q4-report)
Audit logs: {len(log_entries)} entries with valid chain

Demo flow:  Dashboard → Agents → Policies → Approvals → Logs (verify chain)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
