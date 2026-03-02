#!/usr/bin/env python3
"""
AgentGuard Demo Setup
=====================
Run this ONCE before the demo. It will:
  1. Create the "WebResearchBot" agent
  2. Set up its policy (allow web search + DB write, deny sensitive tables)
  3. Save the agent credentials to .demo_agent.env

Usage:
    python demo_setup.py
    python demo_setup.py --reset          # delete existing and recreate
    python demo_setup.py --with-approval  # add require_approval rule on delete:database
                                          # (enables the --scenario approval demo)
"""
import argparse
import sys
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def load_env_file(path):
    """Parse a .env file into a dict, ignoring comments and blanks."""
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip().strip("\"'")
    except FileNotFoundError:
        pass
    return env


# ── resolve paths ─────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent          # sdk/examples/
SDK_DIR      = SCRIPT_DIR.parent              # sdk/
PROJECT_ROOT = SDK_DIR.parent                 # project root
CREDS_FILE   = SCRIPT_DIR / ".demo_agent.env"

# Load admin key: try root .env first, then backend/.env
env = load_env_file(PROJECT_ROOT / ".env")
env.update(load_env_file(PROJECT_ROOT / "backend" / ".env"))

ADMIN_KEY   = env.get("ADMIN_API_KEY", "admin123")
BACKEND_URL = env.get("AGENTGUARD_URL", "http://localhost:8000")

# Make sdk/ importable
sys.path.insert(0, str(SDK_DIR))
from agentguard import AgentGuardClient  # noqa: E402


# ── policy definition ─────────────────────────────────────────────────────────

DEMO_POLICY_ALLOW = [
    {"action": "search:web",      "resource": "*"},
    {"action": "write:database",  "resource": "research_findings"},
]

DEMO_POLICY_DENY = [
    {"action": "delete:*",        "resource": "*"},
    {"action": "write:database",  "resource": "users"},
    {"action": "write:database",  "resource": "payments"},
    {"action": "write:database",  "resource": "logs"},
]

# Used with --with-approval: replace the blanket deny on delete with a
# require_approval rule for delete:database on research_findings so the
# --scenario approval demo flow can demonstrate HITL checkpoints.
DEMO_POLICY_ALLOW_WITH_APPROVAL = [
    {"action": "search:web",      "resource": "*"},
    {"action": "write:database",  "resource": "research_findings"},
]

DEMO_POLICY_DENY_WITH_APPROVAL = [
    {"action": "delete:*",        "resource": "users"},
    {"action": "delete:*",        "resource": "payments"},
    {"action": "delete:*",        "resource": "logs"},
    {"action": "write:database",  "resource": "users"},
    {"action": "write:database",  "resource": "payments"},
    {"action": "write:database",  "resource": "logs"},
]

DEMO_POLICY_REQUIRE_APPROVAL = [
    {"action": "delete:database", "resource": "research_findings"},
]


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing demo agent and recreate")
    parser.add_argument("--with-approval", action="store_true",
                        help="Add require_approval rule for delete:database "
                             "(enables --scenario approval in demo_agent.py)")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║       AgentGuard — Demo Setup                ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Backend : {BACKEND_URL}")
    print(f"  Admin   : {ADMIN_KEY[:4]}{'*' * (len(ADMIN_KEY) - 4)}")
    if args.with_approval:
        print("  Mode    : with human-in-the-loop approval rules")
    print()

    admin = AgentGuardClient(base_url=BACKEND_URL, admin_key=ADMIN_KEY)

    # ── verify backend is reachable ──────────────────────────────────────────
    try:
        import requests
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        print("  [✓] Backend is healthy")
    except Exception as e:
        print(f"  [✗] Cannot reach backend at {BACKEND_URL}")
        print(f"      {e}")
        print()
        print("  Make sure the backend is running:")
        print("    cd backend && python -m uvicorn app.main:app --reload")
        sys.exit(1)

    # ── check for existing agent ─────────────────────────────────────────────
    existing_creds = load_env_file(CREDS_FILE)
    existing_id    = existing_creds.get("DEMO_AGENT_ID")

    if existing_id and not args.reset:
        try:
            agent = admin.get_agent(existing_id)
            print(f"  [✓] Demo agent already exists: {agent['name']}")
            print(f"      Agent ID : {existing_id}")
            print(f"      API Key  : {existing_creds.get('DEMO_AGENT_KEY', '?')[:20]}...")
            print()

            if args.with_approval:
                print("  [~] --with-approval: updating policy to add require_approval rule...")
                policy = admin.set_policy(
                    agent_id=existing_id,
                    allow=DEMO_POLICY_ALLOW_WITH_APPROVAL,
                    deny=DEMO_POLICY_DENY_WITH_APPROVAL,
                    require_approval=DEMO_POLICY_REQUIRE_APPROVAL,
                )
                print(f"        Allow rules   : {len(policy['allow'])}")
                for r in policy["allow"]:
                    print(f"          ✓  {r['action']}  →  {r['resource']}")
                print(f"        Deny rules    : {len(policy['deny'])}")
                print(f"        Approval rules: {len(policy.get('require_approval', []))}")
                for r in policy.get("require_approval", []):
                    print(f"          ⏳  {r['action']}  →  {r['resource']}")
                print()

                # Verify policy was saved correctly — write:database must be in allow, NOT require_approval
                allow_actions = [r["action"] for r in policy["allow"]]
                approval_actions = [r["action"] for r in policy.get("require_approval", [])]
                if "write:database" not in allow_actions or "write:database" in approval_actions:
                    print("  [!] POLICY VERIFICATION FAILED — write:database is not in the allow list.")
                    print("      This is caused by a stale policy in the database.")
                    print("      Fix:  python demo_setup.py --reset --with-approval")
                    sys.exit(1)
                print("  [✓] Policy verified — write:database is correctly in allow")

            _print_run_instructions(args.with_approval)
            return
        except Exception:
            print("  [!] Saved agent not found on server — recreating...")
            print()

    if existing_id and args.reset:
        print("  [~] --reset: removing previous demo agent...")
        try:
            admin.delete_agent(existing_id)
            print(f"      Deleted {existing_id}")
        except Exception:
            print("      (agent already removed)")
        print()

    # ── step 1: create agent ─────────────────────────────────────────────────
    print("  [1/3] Creating WebResearchBot agent...")
    agent    = admin.create_agent(
        name="WebResearchBot",
        owner_team="research-team",
        environment="production",
    )
    agent_id = agent["agent_id"]
    api_key  = agent["api_key"]
    print(f"        Agent ID : {agent_id}")
    print(f"        API Key  : {api_key}")
    print()

    # ── step 2: set policy ───────────────────────────────────────────────────
    print("  [2/3] Setting policy...")
    if args.with_approval:
        policy = admin.set_policy(
            agent_id=agent_id,
            allow=DEMO_POLICY_ALLOW_WITH_APPROVAL,
            deny=DEMO_POLICY_DENY_WITH_APPROVAL,
            require_approval=DEMO_POLICY_REQUIRE_APPROVAL,
        )
    else:
        policy = admin.set_policy(
            agent_id=agent_id,
            allow=DEMO_POLICY_ALLOW,
            deny=DEMO_POLICY_DENY,
        )

    print(f"        Allow rules   : {len(policy['allow'])}")
    for r in policy["allow"]:
        print(f"          ✓  {r['action']}  →  {r['resource']}")
    print(f"        Deny rules    : {len(policy['deny'])}")
    for r in policy["deny"]:
        print(f"          ✗  {r['action']}  →  {r['resource']}")
    approval_rules = policy.get("require_approval", [])
    if approval_rules:
        print(f"        Approval rules: {len(approval_rules)}")
        for r in approval_rules:
            print(f"          ⏳  {r['action']}  →  {r['resource']}")
    print()

    # ── step 3: save credentials ─────────────────────────────────────────────
    print(f"  [3/3] Saving credentials → {CREDS_FILE.name}")
    with open(CREDS_FILE, "w") as f:
        f.write(f"DEMO_AGENT_ID={agent_id}\n")
        f.write(f"DEMO_AGENT_KEY={api_key}\n")
        f.write(f"DEMO_ADMIN_KEY={ADMIN_KEY}\n")
        f.write(f"AGENTGUARD_URL={BACKEND_URL}\n")
    print(f"        Saved to {CREDS_FILE}")
    print()

    print("  ╔══════════════════════════════════════════════╗")
    print("  ║  Setup complete!                             ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    _print_run_instructions(args.with_approval)


def _print_run_instructions(with_approval: bool):
    print("  Run the demo agent:")
    print("    python demo_agent.py                        # normal flow")
    if with_approval:
        print("    python demo_agent.py --scenario approval    # HITL approval flow")
    print()
    print("  Open the UI live demo page:")
    print("    http://localhost:3000/demo")
    if with_approval:
        print("  Open the approvals page to handle approval requests:")
        print("    http://localhost:3000/approvals")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
