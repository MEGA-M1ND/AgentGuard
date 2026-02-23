#!/usr/bin/env python3
"""
AgentGuard Demo Agent — WebResearchBot
=======================================
Simulates a LangGraph-style web research + database update pipeline
with AgentGuard governance checks at every step.

Usage:
    python demo_agent.py                        # 1 run, first topic
    python demo_agent.py --loop 3               # 3 runs, different topics
    python demo_agent.py --topic "quantum AI"   # custom topic, 1 run
    python demo_agent.py --topic "LLMs" --loop 2

Demo flow per run:
    Step 1 → enforce("search:web")       → AgentGuard decides
    Step 2 → [mock] execute web search
    Step 3 → enforce("write:database")   → AgentGuard decides
    Step 4 → [mock] write to DB          → (or blocked)

Watch the live audit trail at: http://localhost:3000/demo
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


def count_research_findings() -> int:
    if not RESEARCH_DB_FILE.exists():
        return 0
    conn  = sqlite3.connect(RESEARCH_DB_FILE)
    count = conn.execute("SELECT COUNT(*) FROM research_findings").fetchone()[0]
    conn.close()
    return count


# ── agent pipeline ────────────────────────────────────────────────────────────

def run_agent(client: AgentGuardClient, topic: str, run_num: int):
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


# ── entrypoint ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AgentGuard Demo Agent — WebResearchBot"
    )
    parser.add_argument("--topic", default=None,
                        help="Research topic override")
    parser.add_argument("--loop",  type=int, default=1,
                        help="Number of agent runs (default: 1)")
    args = parser.parse_args()

    init_research_db()

    print()
    print(f"  {BOLD}AgentGuard  ·  WebResearchBot Demo{RST}")
    print(f"  {DIM}Backend  : {BACKEND_URL}{RST}")
    print(f"  {DIM}Agent    : {AGENT_ID}{RST}")
    print(f"  {DIM}Live UI  : http://localhost:3000/demo{RST}")
    print(f"  {DIM}Research DB : {RESEARCH_DB_FILE}{RST}")
    print(f"  {DIM}Existing rows in research_findings: {count_research_findings()}{RST}")

    client = AgentGuardClient(base_url=BACKEND_URL, agent_key=AGENT_KEY)

    if args.topic:
        topics = [args.topic] * args.loop
    else:
        topics = (TOPICS * ((args.loop // len(TOPICS)) + 1))[:args.loop]

    for i, topic in enumerate(topics, 1):
        run_agent(client, topic, i)
        if i < len(topics):
            print(f"\n  {DIM}  Next run in 3 seconds…{RST}")
            time.sleep(3)

    print()
    print(f"  {'─' * 56}")
    print(f"  {BLU}  View full audit trail at:{RST}")
    print(f"  {BLU}  http://localhost:3000/demo{RST}")
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
