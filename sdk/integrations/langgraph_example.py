"""
AgentGuard + LangGraph Integration Example
==========================================
Shows how to wrap LangGraph nodes with AgentGuard policy enforcement.

Every node that performs a sensitive action:
  1. Calls guard.enforce()  — ask AgentGuard for permission
  2. Executes (or aborts)   — based on the decision
  3. Calls guard.log_action() — record what happened

Install:
    pip install agentguard-sdk langgraph

Usage:
    export AGENTGUARD_URL=http://localhost:8000
    export AGENTGUARD_AGENT_KEY=agk_your_key
    python langgraph_example.py
"""
import os
import uuid
from typing import TypedDict

from agentguard import AgentGuardClient

# ── Replace with your own search / DB functions ───────────────────────────────

def run_web_search(query: str) -> list[dict]:
    """Stub — replace with Tavily, SerpAPI, etc."""
    return [
        {"title": f"Result 1 for {query}", "url": "https://example.com/1"},
        {"title": f"Result 2 for {query}", "url": "https://example.com/2"},
    ]

def write_to_db(table: str, rows: list[dict]) -> None:
    """Stub — replace with your actual DB client."""
    print(f"    [DB] Wrote {len(rows)} rows to {table}")

# ── AgentGuard client ─────────────────────────────────────────────────────────

guard = AgentGuardClient(
    base_url=os.environ.get("AGENTGUARD_URL", "http://localhost:8000"),
    agent_key=os.environ.get("AGENTGUARD_AGENT_KEY", ""),
)

# ── LangGraph state ───────────────────────────────────────────────────────────

class ResearchState(TypedDict):
    query:   str
    results: list
    status:  str
    run_id:  str

# ── Guarded nodes ─────────────────────────────────────────────────────────────

def web_search_node(state: ResearchState) -> ResearchState:
    """Node 1: enforce → search → log."""
    query = state["query"]
    ctx   = {"run_id": state["run_id"], "node": "web_search"}

    decision = guard.enforce(action="search:web", resource=query, context=ctx)

    if not decision["allowed"]:
        guard.log_action(
            action="search:web", resource=query,
            allowed=False, result="error", context=ctx,
            metadata={"reason": decision["reason"]},
        )
        return {**state, "status": f"blocked: {decision['reason']}", "results": []}

    results = run_web_search(query)
    guard.log_action(
        action="search:web", resource=query,
        allowed=True, result="success", context=ctx,
        metadata={"result_count": len(results)},
    )
    return {**state, "results": results, "status": "searched"}


def db_write_node(state: ResearchState) -> ResearchState:
    """Node 2: enforce → write → log."""
    table = "research_findings"
    ctx   = {"run_id": state["run_id"], "node": "db_write"}

    if not state["results"]:
        return {**state, "status": "skipped (no results)"}

    decision = guard.enforce(action="write:database", resource=table, context=ctx)

    if not decision["allowed"]:
        guard.log_action(
            action="write:database", resource=table,
            allowed=False, result="error", context=ctx,
            metadata={"reason": decision["reason"]},
        )
        return {**state, "status": f"blocked: {decision['reason']}"}

    write_to_db(table, state["results"])
    guard.log_action(
        action="write:database", resource=table,
        allowed=True, result="success", context=ctx,
        metadata={"rows_written": len(state["results"])},
    )
    return {**state, "status": "done"}

# ── Build graph ───────────────────────────────────────────────────────────────

try:
    from langgraph.graph import StateGraph

    builder = StateGraph(ResearchState)
    builder.add_node("web_search", web_search_node)
    builder.add_node("db_write",   db_write_node)
    builder.set_entry_point("web_search")
    builder.add_edge("web_search", "db_write")
    graph = builder.compile()

    def run(query: str) -> ResearchState:
        return graph.invoke({
            "query":   query,
            "results": [],
            "status":  "starting",
            "run_id":  str(uuid.uuid4())[:8],
        })

except ImportError:
    # LangGraph not installed — show the pattern without the framework
    def run(query: str) -> ResearchState:  # type: ignore[misc]
        state: ResearchState = {
            "query": query, "results": [], "status": "starting",
            "run_id": str(uuid.uuid4())[:8],
        }
        state = web_search_node(state)
        state = db_write_node(state)
        return state

# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run("AI agent governance 2025")
    print(f"\nFinal status : {result['status']}")
    print(f"Results found: {len(result['results'])}")
    print("View audit trail: http://localhost:3000/logs")
