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
    python demo_setup.py --reset    # delete existing and recreate
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


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Delete existing demo agent and recreate")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║       AgentGuard — Demo Setup                ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Backend : {BACKEND_URL}")
    print(f"  Admin   : {ADMIN_KEY[:4]}{'*' * (len(ADMIN_KEY) - 4)}")
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
            print("  ─────────────────────────────────────────────")
            print("  Ready! Run the demo agent in another terminal:")
            print()
            print("    python demo_agent.py")
            print()
            print("  Then open the UI live demo page:")
            print("    http://localhost:3000/demo")
            print("  ─────────────────────────────────────────────")
            print()
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
    policy = admin.set_policy(
        agent_id=agent_id,
        allow=DEMO_POLICY_ALLOW,
        deny=DEMO_POLICY_DENY,
    )
    print(f"        Allow rules : {len(policy['allow'])}")
    for r in policy["allow"]:
        print(f"          ✓  {r['action']}  →  {r['resource']}")
    print(f"        Deny rules  : {len(policy['deny'])}")
    for r in policy["deny"]:
        print(f"          ✗  {r['action']}  →  {r['resource']}")
    print()

    # ── step 3: save credentials ─────────────────────────────────────────────
    print(f"  [3/3] Saving credentials → {CREDS_FILE.name}")
    with open(CREDS_FILE, "w") as f:
        f.write(f"DEMO_AGENT_ID={agent_id}\n")
        f.write(f"DEMO_AGENT_KEY={api_key}\n")
        f.write(f"AGENTGUARD_URL={BACKEND_URL}\n")
    print(f"        Saved to {CREDS_FILE}")
    print()

    print("  ╔══════════════════════════════════════════════╗")
    print("  ║  Setup complete!                             ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print("  Run the demo agent:")
    print("    python demo_agent.py")
    print()
    print("  Open the UI live demo page:")
    print("    http://localhost:3000/demo")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
