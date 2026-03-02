"""
Playground seed — creates or updates WebResearchBot with a policy
that matches all playground example prompts exactly.

Run once after the server is started:
    python playground_seed.py

Policy design:
  ✅ Allow:    search:*, read:*, fetch:*  (any resource)
  🚫 Deny:     delete:*,  write:database,  write:production
  ⏳ Approval: export:*  (any resource)

This makes the example prompts work as expected:
  - "Search for news"           → allowed  (search:*)
  - "Read stock prices"         → allowed  (read:*)
  - "Fetch research papers"     → allowed  (fetch:*)
  - "Delete database records"   → denied   (delete:*)
  - "Write to production DB"    → denied   (write:database)
  - "Export dataset to CSV"     → pending  (export:*)
  - Injection prompts           → blocked before enforcement
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
ADMIN_KEY = "admin123"


def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Admin-Key", ADMIN_KEY)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()
        print(f"  ERROR {e.code} on {method} {path}: {body_txt[:300]}")
        return None


WEBRESEACHBOT_POLICY = {
    # API field names: allow / deny / require_approval  (NOT allow_rules etc.)
    "allow": [
        {"action": "search:*",  "resource": "*"},
        {"action": "read:*",    "resource": "*"},
        {"action": "fetch:*",   "resource": "*"},
        {"action": "query:*",   "resource": "*"},
        {"action": "browse:*",  "resource": "*"},
    ],
    "deny": [
        {"action": "delete:*",  "resource": "*"},
        {"action": "remove:*",  "resource": "*"},
        {"action": "drop:*",    "resource": "*"},
        {"action": "truncate:*","resource": "*"},
        {"action": "write:*",   "resource": "production*"},
        {"action": "write:*",   "resource": "*database*"},
    ],
    "require_approval": [
        {"action": "export:*",  "resource": "*"},
        {"action": "send:*",    "resource": "*"},
        {"action": "transfer:*","resource": "*"},
    ],
}


def main():
    print("\n🔧 Setting up WebResearchBot for the Playground...\n")

    # Check server
    try:
        with urllib.request.urlopen(BASE + "/health") as r:
            pass
    except Exception:
        print("❌ Cannot reach server at http://localhost:8000 — is it running?")
        sys.exit(1)

    # Find existing WebResearchBot
    agents = call("GET", "/agents") or []
    bot = next((a for a in agents if a.get("name") == "WebResearchBot"), None)

    if bot:
        agent_id = bot["agent_id"]
        print(f"  ✓ Found existing WebResearchBot  ({agent_id})")
    else:
        print("  WebResearchBot not found — creating it...")
        bot = call("POST", "/agents", {
            "name": "WebResearchBot",
            "owner_team": "research-team",
            "environment": "production",
        })
        if not bot:
            print("  ❌ Failed to create agent")
            sys.exit(1)
        agent_id = bot["agent_id"]
        print(f"  ✓ Created WebResearchBot  ({agent_id})")
        if bot.get("api_key"):
            print(f"     API key: {bot['api_key']}")

    # Apply policy
    result = call("PUT", f"/agents/{agent_id}/policy", WEBRESEACHBOT_POLICY)
    if result:
        print("  ✓ Policy applied:")
        print("      Allow:    search:*  read:*  fetch:*  query:*  browse:*")
        print("      Deny:     delete:*  write:database  write:production*")
        print("      Approval: export:*  send:*  transfer:*")
    else:
        print("  ❌ Failed to set policy")
        sys.exit(1)

    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  WebResearchBot is ready for the Playground!

Open the Playground:  http://localhost:3000/playground

Expected results for example prompts:
  ✅ "Search for latest news..."          → Allowed
  ✅ "Fetch research papers..."           → Allowed
  ✅ "Read current stock prices..."       → Allowed
  🚫 "Delete all cached records..."       → Denied
  🚫 "Write raw data to production DB..."  → Denied
  ⏳ "Export full dataset to CSV..."      → Pending Approval
  💉 Injection prompts                    → Blocked (before enforcement)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
