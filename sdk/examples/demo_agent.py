#!/usr/bin/env python3
"""
AgentGuard Demo Agent — WebResearchBot
=======================================
Simulates a LangGraph-style web research + database update pipeline
with AgentGuard governance checks at every step.

Usage:
    python demo_agent.py                             # normal flow (1 run)
    python demo_agent.py --loop 3                    # 3 runs, different topics
    python demo_agent.py --topic "quantum AI"        # custom topic
    python demo_agent.py --scenario approval         # HITL approval demo
    python demo_agent.py --scenario approval --loop 2

Demo flows:
  normal   — Steps 1-4: enforce search → search → enforce write → write to DB
  approval — Steps 1-4 as above, then Step 5: enforce delete:database →
             AgentGuard returns 'pending' → agent waits for human approval
             at http://localhost:3000/approvals → continues or aborts based
             on the human decision.

Pre-requisites for --scenario approval:
    python demo_setup.py --with-approval   # sets require_approval rule on delete:database

Watch the live audit trail at: http://localhost:3000/demo
Watch pending approvals at:    http://localhost:3000/approvals
"""
import argparse
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


# ── resolve paths ─────────────────────────────────────────────────────────────

SCRIPT_DIR        = Path(__file__).parent
SDK_DIR           = SCRIPT_DIR.parent
CREDS_FILE        = SCRIPT_DIR / ".demo_agent.env"
RESEARCH_DB_FILE  = SCRIPT_DIR / "research_findings.db"


def load_env_file(path):
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


if not CREDS_FILE.exists():
    print()
    print("  [ERROR] Demo agent not set up.")
    print("  Run first:  python demo_setup.py")
    print()
    sys.exit(1)

creds = load_env_file(CREDS_FILE)
AGENT_KEY   = creds.get("DEMO_AGENT_KEY", "")
AGENT_ID    = creds.get("DEMO_AGENT_ID", "")
ADMIN_KEY   = creds.get("DEMO_ADMIN_KEY", "")
BACKEND_URL = creds.get("AGENTGUARD_URL", "http://localhost:8000")

if not AGENT_KEY:
    print("  [ERROR] DEMO_AGENT_KEY missing from .demo_agent.env")
    print("  Run:  python demo_setup.py --reset")
    sys.exit(1)

sys.path.insert(0, str(SDK_DIR))
from agentguard import AgentGuardClient  # noqa: E402


# ── ANSI colours ──────────────────────────────────────────────────────────────

GRN  = "\033[92m"
RED  = "\033[91m"
YLW  = "\033[93m"
BLU  = "\033[94m"
CYN  = "\033[96m"
AMB  = "\033[33m"
DIM  = "\033[2m"
BOLD = "\033[1m"
RST  = "\033[0m"


# ── mock data ─────────────────────────────────────────────────────────────────

TOPICS = [
    "AI agent frameworks 2025",
    "LangGraph multi-agent systems",
    "vector database benchmarks",
    "LLM fine-tuning techniques",
    "RAG architecture patterns",
    "autonomous agent safety",
]

MOCK_RESULTS = {
    "AI agent frameworks 2025": [
        {"title": "LangGraph: Building Stateful Multi-Agent Systems", "source": "arxiv.org",      "score": 0.97},
        {"title": "AutoGen vs CrewAI: A Comparative Study",           "source": "papers.ml",      "score": 0.91},
        {"title": "The Rise of Agentic AI in 2025",                   "source": "techcrunch.com", "score": 0.88},
    ],
    "LangGraph multi-agent systems": [
        {"title": "LangGraph State Machines Explained",       "source": "docs.langchain.com", "score": 0.99},
        {"title": "Multi-Agent Coordination Patterns",        "source": "arxiv.org",          "score": 0.92},
        {"title": "Supervisor vs Swarm: Architecture Guide",  "source": "medium.com",         "score": 0.85},
    ],
    "vector database benchmarks": [
        {"title": "Pinecone vs Weaviate vs Qdrant — 2025 Benchmark", "source": "benchmarks.ai", "score": 0.96},
        {"title": "ANN Search at Scale: Lessons Learned",            "source": "eng.spotify.com","score": 0.89},
    ],
    "LLM fine-tuning techniques": [
        {"title": "LoRA vs QLoRA: Practical Comparison",         "source": "huggingface.co", "score": 0.94},
        {"title": "RLHF at Scale: What Actually Works",          "source": "openai.com",     "score": 0.91},
        {"title": "DPO: Direct Preference Optimization Explained","source": "arxiv.org",     "score": 0.88},
    ],
}

_DEFAULT_RESULTS = lambda topic: [  # noqa: E731
    {"title": f"Latest findings on {topic}",      "source": "research.ai",  "score": 0.93},
    {"title": f"2025 survey: {topic}",             "source": "arxiv.org",    "score": 0.87},
    {"title": f"Industry report: {topic} trends",  "source": "gartner.com",  "score": 0.82},
]


# ── print helpers ─────────────────────────────────────────────────────────────

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def section(title):
    print(f"\n  {DIM}[{_ts()}]{RST}  {BOLD}{title}{RST}")

def ok(msg):
    print(f"            {GRN}✓{RST}  {msg}")

def denied(msg):
    print(f"            {RED}✗{RST}  {msg}")

def pending_msg(msg):
    print(f"            {AMB}⏳{RST}  {msg}")

def info(msg):
    print(f"            {BLU}→{RST}  {msg}")

def dim(msg):
    print(f"            {DIM}{msg}{RST}")


# ── research_findings database ───────────────────────────────────────────────

def init_research_db():
    """Create research_findings table if it doesn't exist."""
    conn = sqlite3.connect(RESEARCH_DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_findings (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id    TEXT    NOT NULL,
            topic     TEXT    NOT NULL,
            title     TEXT    NOT NULL,
            source    TEXT    NOT NULL,
            score     REAL    NOT NULL,
            saved_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def write_research_findings(run_id: str, topic: str, results: list) -> int:
    """Insert search results into research_findings. Returns rows written."""
    conn = sqlite3.connect(RESEARCH_DB_FILE)
    now  = datetime.utcnow().isoformat()
    rows = [(run_id, topic, r["title"], r["source"], r["score"], now) for r in results]
    conn.executemany(
        "INSERT INTO research_findings (run_id, topic, title, source, score, saved_at) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM research_findings").fetchone()[0]
    conn.close()
    return count


def delete_old_research_findings(run_id: str) -> int:
    """Delete rows for a specific run_id (mocked cleanup). Returns deleted count."""
    conn = sqlite3.connect(RESEARCH_DB_FILE)
    cur = conn.execute("DELETE FROM research_findings WHERE run_id = ?", (run_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def count_research_findings() -> int:
    if not RESEARCH_DB_FILE.exists():
        return 0
    conn  = sqlite3.connect(RESEARCH_DB_FILE)
    count = conn.execute("SELECT COUNT(*) FROM research_findings").fetchone()[0]
    conn.close()
    return count


# ── approval waiting display ──────────────────────────────────────────────────

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

def wait_with_spinner(client: "AgentGuardClient", approval_id: str, timeout: int = 300):
    """
    Poll for approval with an animated spinner using agent auth.
    Returns the final approval dict once a decision is made.
    Raises TimeoutError after `timeout` seconds.
    """
    deadline = time.time() + timeout
    frame    = 0
    poll_interval = 3

    print()
    while time.time() < deadline:
        elapsed = int(time.time() - (deadline - timeout))
        spin    = SPINNER[frame % len(SPINNER)]
        line    = f"            {AMB}{spin}{RST}  Waiting for human decision… ({elapsed}s)"
        print(line, end="\r", flush=True)
        frame += 1

        try:
            # Use agent auth — agents can poll their own approvals without admin creds
            approval = client.poll_approval(approval_id)
            if approval["status"] != "pending":
                print(" " * 70, end="\r")  # clear spinner line
                return approval
        except Exception as e:
            # Transient errors (network blip) — log briefly and keep polling
            print(" " * 70, end="\r")
            print(f"            {DIM}[poll error: {e}]{RST}", end="\r", flush=True)

        time.sleep(poll_interval)

    print(" " * 70, end="\r")
    raise TimeoutError(f"No decision within {timeout}s — still pending in the queue.")


# ── agent pipeline ────────────────────────────────────────────────────────────

def run_agent(client: "AgentGuardClient", topic: str, run_num: int):
    """Standard pipeline: search → write to DB."""
    run_id = str(uuid.uuid4())[:8]
    ctx    = {"run_id": run_id, "topic": topic, "agent": "WebResearchBot"}

    print()
    print(f"  {'═' * 54}")
    print(f"  {BOLD}  WebResearchBot  —  Run #{run_num}{RST}")
    print(f"  {YLW}  Topic  :{RST}  {topic}")
    print(f"  {DIM}  Run ID :  {run_id}{RST}")
    print(f"  {'═' * 54}")

    # ── STEP 1: enforce search:web ────────────────────────────────────────────
    section("STEP 1  ·  Permission check  →  search:web")
    info(f"Action   :  search:web")
    info(f"Resource :  {topic}")
    info(f"Asking AgentGuard …")
    time.sleep(0.5)

    d1 = client.enforce(
        action="search:web",
        resource=topic,
        context={**ctx, "step": 1},
    )

    if not d1["allowed"]:
        denied(f"DENIED  —  {d1['reason']}")
        client.log_action(
            action="search:web", resource=topic,
            allowed=False, result="error",
            context=ctx, metadata={"run_id": run_id, "step": 1, "reason": d1["reason"]},
        )
        print(f"\n  {YLW}  Agent halted — cannot search without permission.{RST}")
        return

    ok(f"ALLOWED  —  {d1['reason']}")
    client.log_action(
        action="search:web", resource=topic,
        allowed=True, result="success",
        context=ctx, metadata={"run_id": run_id, "step": 1},
    )

    # ── STEP 2: execute search (mocked) ──────────────────────────────────────
    section("STEP 2  ·  Executing web search")
    info(f"Searching: {topic}")
    time.sleep(0.9)

    results = MOCK_RESULTS.get(topic, _DEFAULT_RESULTS(topic))
    ok(f"Found {len(results)} results")
    for r in results:
        dim(f"• [{r['score']:.0%}]  {r['title']}  ({r['source']})")

    # ── STEP 3: enforce write:database ────────────────────────────────────────
    section("STEP 3  ·  Permission check  →  write:database")
    info(f"Action   :  write:database")
    info(f"Resource :  research_findings")
    info(f"Asking AgentGuard …")
    time.sleep(0.5)

    d2 = client.enforce(
        action="write:database",
        resource="research_findings",
        context={**ctx, "step": 3},
    )

    if not d2["allowed"]:
        denied(f"DENIED  —  {d2['reason']}")
        client.log_action(
            action="write:database", resource="research_findings",
            allowed=False, result="error",
            context=ctx, metadata={"run_id": run_id, "step": 3, "reason": d2["reason"]},
        )
        print()
        print(f"  {RED}  ┌{'─' * 52}┐{RST}")
        print(f"  {RED}  │  DB write BLOCKED by AgentGuard policy  ✗      │{RST}")
        print(f"  {RED}  │  Research data NOT saved — governance enforced  │{RST}")
        print(f"  {RED}  └{'─' * 52}┘{RST}")
        return

    ok(f"ALLOWED  —  {d2['reason']}")

    # ── STEP 4: write to DB (real SQLite write) ───────────────────────────────
    section("STEP 4  ·  Writing to database")
    info(f"Table  :  research_findings")
    info(f"File   :  {RESEARCH_DB_FILE}")
    info(f"Rows   :  {len(results)}")
    time.sleep(0.7)

    total = write_research_findings(run_id, topic, results)
    ok(f"Wrote {len(results)} rows  (run_id={run_id})")
    ok(f"Total rows in research_findings: {total}")

    client.log_action(
        action="write:database", resource="research_findings",
        allowed=True, result="success",
        context=ctx,
        metadata={"run_id": run_id, "step": 4, "rows_written": len(results), "total_rows": total, "topic": topic},
    )

    print()
    print(f"  {GRN}  ┌{'─' * 52}┐{RST}")
    print(f"  {GRN}  │  Run complete — all governance checks passed  ✓   │{RST}")
    print(f"  {GRN}  │  {len(results)} rows saved to research_findings.db         │{RST}")
    print(f"  {GRN}  └{'─' * 52}┘{RST}")


def run_agent_with_approval(client: "AgentGuardClient", topic: str, run_num: int):
    """
    Extended pipeline that adds Step 5: delete:database requiring human approval.

    Demonstrates the Human-in-the-Loop (HITL) governance checkpoint:
      1. Agent attempts to clean up old research rows
      2. AgentGuard returns status='pending' + approval_id
      3. Agent waits (spinner) while a human reviews the request
      4. Human approves → agent proceeds; Human denies → agent aborts

    Requires the demo policy to have a require_approval rule for delete:database.
    Run  python demo_setup.py --with-approval  to configure this.
    """
    if not ADMIN_KEY:
        print(f"\n  {RED}[ERROR]{RST}  DEMO_ADMIN_KEY not found in {CREDS_FILE}")
        print("  Re-run:  python demo_setup.py --with-approval")
        print("  (This saves the admin key so the agent can poll approval status.)")
        sys.exit(1)

    run_id = str(uuid.uuid4())[:8]
    ctx    = {"run_id": run_id, "topic": topic, "agent": "WebResearchBot", "scenario": "approval"}

    print()
    print(f"  {'═' * 60}")
    print(f"  {BOLD}  WebResearchBot  —  HITL Approval Demo  —  Run #{run_num}{RST}")
    print(f"  {YLW}  Topic  :{RST}  {topic}")
    print(f"  {DIM}  Run ID :  {run_id}{RST}")
    print(f"  {'═' * 60}")

    # ── STEP 1: enforce search:web ────────────────────────────────────────────
    section("STEP 1  ·  Permission check  →  search:web")
    info("Action   :  search:web")
    info(f"Resource :  {topic}")
    info("Asking AgentGuard …")
    time.sleep(0.5)

    d1 = client.enforce(action="search:web", resource=topic, context={**ctx, "step": 1})

    if not d1["allowed"]:
        denied(f"DENIED  —  {d1['reason']}")
        client.log_action(action="search:web", resource=topic, allowed=False, result="error",
                          context=ctx, metadata={"step": 1})
        print(f"\n  {YLW}  Agent halted.{RST}")
        return

    ok(f"ALLOWED  —  {d1['reason']}")
    client.log_action(action="search:web", resource=topic, allowed=True, result="success",
                      context=ctx, metadata={"step": 1})

    # ── STEP 2: web search ────────────────────────────────────────────────────
    section("STEP 2  ·  Executing web search")
    info(f"Searching: {topic}")
    time.sleep(0.9)
    results = MOCK_RESULTS.get(topic, _DEFAULT_RESULTS(topic))
    ok(f"Found {len(results)} results")
    for r in results:
        dim(f"• [{r['score']:.0%}]  {r['title']}  ({r['source']})")

    # ── STEP 3: enforce write:database ────────────────────────────────────────
    section("STEP 3  ·  Permission check  →  write:database")
    info("Action   :  write:database")
    info("Resource :  research_findings")
    info("Asking AgentGuard …")
    time.sleep(0.5)

    d2 = client.enforce(action="write:database", resource="research_findings",
                        context={**ctx, "step": 3})

    if d2["status"] == "pending":
        # write:database requires approval (policy may have it in require_approval)
        approval_id = d2["approval_id"]
        pending_msg(f"PENDING  —  Approval required!")
        info(f"Approval ID :  {approval_id}")
        print()
        print(f"  {AMB}  ┌{'─' * 58}┐{RST}")
        print(f"  {AMB}  │  A human must approve this action before it proceeds.  │{RST}")
        print(f"  {AMB}  │                                                         │{RST}")
        print(f"  {AMB}  │  Open:  http://localhost:3000/approvals                 │{RST}")
        print(f"  {AMB}  │  Click Approve or Deny for the pending request.         │{RST}")
        print(f"  {AMB}  └{'─' * 58}┘{RST}")
        try:
            final = wait_with_spinner(client, approval_id, timeout=300)
        except TimeoutError:
            print()
            pending_msg("Timed out after 5 minutes — request still pending in the queue.")
            client.log_action(action="write:database", resource="research_findings",
                              allowed=False, result="error", context=ctx,
                              metadata={"step": 3, "approval_id": approval_id, "outcome": "timeout"})
            return
        if final["status"] == "approved":
            decision_by = final.get("decision_by", "admin")
            print()
            ok(f"APPROVED by {decision_by} — proceeding with DB write")
            client.log_action(action="write:database", resource="research_findings",
                              allowed=True, result="success", context=ctx,
                              metadata={"step": 3, "approved_by": decision_by, "approval_id": approval_id})
        else:
            decision_by = final.get("decision_by", "admin")
            reason      = final.get("decision_reason", "")
            print()
            denied(f"DENIED by {decision_by}" + (f"  — \"{reason}\"" if reason else ""))
            client.log_action(action="write:database", resource="research_findings",
                              allowed=False, result="error", context=ctx,
                              metadata={"step": 3, "denied_by": decision_by, "approval_id": approval_id})
            print(f"\n  {RED}  DB write denied by human administrator.{RST}")
            return
    elif not d2["allowed"]:
        denied(f"DENIED  —  {d2['reason']}")
        client.log_action(action="write:database", resource="research_findings",
                          allowed=False, result="error", context=ctx, metadata={"step": 3})
        print(f"\n  {RED}  DB write BLOCKED.{RST}")
        return
    else:
        ok(f"ALLOWED  —  {d2['reason']}")

    # ── STEP 4: write results ─────────────────────────────────────────────────
    section("STEP 4  ·  Writing to database")
    info("Table  :  research_findings")
    info(f"Rows   :  {len(results)}")
    time.sleep(0.7)

    total = write_research_findings(run_id, topic, results)
    ok(f"Wrote {len(results)} rows  (run_id={run_id})")
    ok(f"Total rows in research_findings: {total}")
    client.log_action(action="write:database", resource="research_findings",
                      allowed=True, result="success", context=ctx,
                      metadata={"step": 4, "rows_written": len(results), "topic": topic})

    # ── STEP 5: request approval to delete old entries ────────────────────────
    section("STEP 5  ·  Human-in-the-Loop checkpoint  →  delete:database")
    info("Action   :  delete:database")
    info("Resource :  research_findings")
    info("Context  :  routine cleanup — remove stale entries from this run")
    info("Asking AgentGuard …")
    time.sleep(0.5)

    d3 = client.enforce(
        action="delete:database",
        resource="research_findings",
        context={**ctx, "step": 5, "reason": "cleanup stale entries", "run_id": run_id},
    )

    if d3["status"] == "allowed":
        # Shouldn't happen with the approval policy, but handle gracefully
        ok(f"ALLOWED  —  {d3['reason']}")
        deleted = delete_old_research_findings(run_id)
        ok(f"Deleted {deleted} rows for run_id={run_id}")

    elif d3["status"] == "pending":
        approval_id = d3["approval_id"]
        pending_msg(f"PENDING  —  Approval required!")
        info(f"Approval ID :  {approval_id}")
        print()
        print(f"  {AMB}  ┌{'─' * 58}┐{RST}")
        print(f"  {AMB}  │  A human must approve this action before it proceeds.  │{RST}")
        print(f"  {AMB}  │                                                         │{RST}")
        print(f"  {AMB}  │  Open:  http://localhost:3000/approvals                 │{RST}")
        print(f"  {AMB}  │  Click Approve or Deny for the pending request.         │{RST}")
        print(f"  {AMB}  └{'─' * 58}┘{RST}")

        try:
            final = wait_with_spinner(client, approval_id, timeout=300)
        except TimeoutError:
            print()
            pending_msg("Timed out after 5 minutes — request still pending in the queue.")
            client.log_action(action="delete:database", resource="research_findings",
                              allowed=False, result="error", context=ctx,
                              metadata={"step": 5, "approval_id": approval_id, "outcome": "timeout"})
            return

        if final["status"] == "approved":
            decision_by = final.get("decision_by", "admin")
            reason      = final.get("decision_reason", "")
            print()
            ok(f"APPROVED by {decision_by}" + (f"  — \"{reason}\"" if reason else ""))
            section("STEP 5b  ·  Executing approved delete")
            info(f"Removing stale entries for run_id={run_id}…")
            time.sleep(0.5)
            deleted = delete_old_research_findings(run_id)
            ok(f"Deleted {deleted} rows  (run_id={run_id})")
            client.log_action(action="delete:database", resource="research_findings",
                              allowed=True, result="success", context=ctx,
                              metadata={"step": 5, "deleted_rows": deleted,
                                        "approved_by": decision_by, "approval_id": approval_id})

            print()
            print(f"  {GRN}  ┌{'─' * 58}┐{RST}")
            print(f"  {GRN}  │  Run complete — HITL approval checkpoint passed  ✓   │{RST}")
            print(f"  {GRN}  │  {len(results)} rows written, {deleted} stale rows cleaned up          │{RST}")
            print(f"  {GRN}  └{'─' * 58}┘{RST}")

        else:  # denied
            decision_by = final.get("decision_by", "admin")
            reason      = final.get("decision_reason", "")
            print()
            denied(f"DENIED by {decision_by}" + (f"  — \"{reason}\"" if reason else ""))
            client.log_action(action="delete:database", resource="research_findings",
                              allowed=False, result="error", context=ctx,
                              metadata={"step": 5, "denied_by": decision_by,
                                        "decision_reason": reason, "approval_id": approval_id})

            print()
            print(f"  {RED}  ┌{'─' * 58}┐{RST}")
            print(f"  {RED}  │  Delete denied by human administrator             ✗   │{RST}")
            print(f"  {RED}  │  Research data preserved — governance enforced        │{RST}")
            print(f"  {RED}  └{'─' * 58}┘{RST}")

    else:
        # outright denied by policy (no require_approval rule set up)
        denied(f"DENIED  —  {d3['reason']}")
        print()
        print(f"  {YLW}  Hint: run  python demo_setup.py --with-approval  to enable HITL.{RST}")
        client.log_action(action="delete:database", resource="research_findings",
                          allowed=False, result="error", context=ctx,
                          metadata={"step": 5, "reason": d3["reason"]})


# ── entrypoint ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AgentGuard Demo Agent — WebResearchBot"
    )
    parser.add_argument("--topic", default=None,
                        help="Research topic override")
    parser.add_argument("--loop",  type=int, default=1,
                        help="Number of agent runs (default: 1)")
    parser.add_argument("--scenario", default="normal",
                        choices=["normal", "approval"],
                        help="Demo scenario: 'normal' (default) or 'approval' (HITL demo)")
    args = parser.parse_args()

    init_research_db()

    print()
    print(f"  {BOLD}AgentGuard  ·  WebResearchBot Demo{RST}")
    print(f"  {DIM}Backend     : {BACKEND_URL}{RST}")
    print(f"  {DIM}Agent       : {AGENT_ID}{RST}")
    print(f"  {DIM}Scenario    : {args.scenario}{RST}")
    print(f"  {DIM}Live UI     : http://localhost:3000/demo{RST}")
    if args.scenario == "approval":
        print(f"  {AMB}  Approvals : http://localhost:3000/approvals{RST}")
    print(f"  {DIM}Research DB : {RESEARCH_DB_FILE}{RST}")
    print(f"  {DIM}Existing rows in research_findings: {count_research_findings()}{RST}")

    # Build client — approval scenario needs admin_key for polling approval status
    client = AgentGuardClient(
        base_url=BACKEND_URL,
        agent_key=AGENT_KEY,
        admin_key=ADMIN_KEY if ADMIN_KEY else None,
    )

    if args.topic:
        topics = [args.topic] * args.loop
    else:
        topics = (TOPICS * ((args.loop // len(TOPICS)) + 1))[:args.loop]

    for i, topic in enumerate(topics, 1):
        if args.scenario == "approval":
            run_agent_with_approval(client, topic, i)
        else:
            run_agent(client, topic, i)
        if i < len(topics):
            print(f"\n  {DIM}  Next run in 3 seconds…{RST}")
            time.sleep(3)

    print()
    print(f"  {'─' * 56}")
    print(f"  {BLU}  View full audit trail at:{RST}")
    print(f"  {BLU}  http://localhost:3000/demo{RST}")
    if args.scenario == "approval":
        print(f"  {BLU}  View approvals at:{RST}")
        print(f"  {BLU}  http://localhost:3000/approvals{RST}")
    print(f"  {'─' * 56}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  [Stopped by user]")
    except Exception as e:
        print(f"\n  {RED}[ERROR]{RST}  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
