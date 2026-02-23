# AgentGuard SDK

[![PyPI version](https://img.shields.io/pypi/v/agentguard-sdk.svg)](https://pypi.org/project/agentguard-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/agentguard-sdk.svg)](https://pypi.org/project/agentguard-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-7289DA)](https://discord.gg/agentguard)

**Identity, permissions, and audit logs for AI agents.**

AgentGuard is the governance layer for production AI agents. Before your agent reads a file, queries a database, or calls an API — it asks AgentGuard. AgentGuard decides. Everything is logged.

Works with **LangGraph**, **AutoGen**, **CrewAI**, and any agent framework.

---

## The Problem

AI agents are deployed into production without the access controls we take for granted for humans:

- No identity — who is this agent?
- No least-privilege — it can do anything it's coded to do
- No audit trail — no record of what it actually did

One misconfigured agent, one prompt injection, one runaway loop — and there is no circuit breaker, no log, and no way to know it happened.

## The Solution

```python
# One check. Before every sensitive action.
result = guard.enforce(action="write:database", resource="users")

if result["allowed"]:
    db.write(data)                          # proceed
    guard.log_action(...)                   # record it
else:
    raise PermissionError(result["reason"]) # blocked — and logged
```

AgentGuard evaluates your agent's policy (deny-first, wildcard rules) and returns an instant allow/deny decision. Change the policy in the dashboard — no agent code changes, no redeployment.

---

## Installation

```bash
pip install agentguard-sdk
```

---

## Quickstart (5 minutes)

### Step 1 — Create an agent (admin, once)

```python
from agentguard import AgentGuardClient

admin = AgentGuardClient(
    base_url="https://your-agentguard-instance.com",
    admin_key="your-admin-key"
)

agent = admin.create_agent(
    name="ResearchBot",
    owner_team="ml-team",
    environment="production"
)

# Set what it can and cannot do
admin.set_policy(
    agent_id=agent["agent_id"],
    allow=[
        {"action": "search:web",     "resource": "*"},
        {"action": "write:database", "resource": "research_findings"},
    ],
    deny=[
        {"action": "delete:*",       "resource": "*"},
        {"action": "write:database", "resource": "users"},
        {"action": "write:database", "resource": "payments"},
    ]
)

print(f"Agent key: {agent['api_key']}")  # save this
```

### Step 2 — Add governance to your agent (runtime)

```python
from agentguard import AgentGuardClient

guard = AgentGuardClient(
    base_url="https://your-agentguard-instance.com",
    agent_key="agk_your_agent_key"
)

def research_and_save(topic: str):
    # Check before searching
    r = guard.enforce(action="search:web", resource=topic)
    if not r["allowed"]:
        raise PermissionError(r["reason"])

    results = web_search(topic)
    guard.log_action(action="search:web", resource=topic,
                     allowed=True, result="success",
                     metadata={"result_count": len(results)})

    # Check before writing
    r = guard.enforce(action="write:database", resource="research_findings")
    if not r["allowed"]:
        guard.log_action(action="write:database", resource="research_findings",
                         allowed=False, result="error",
                         metadata={"reason": r["reason"]})
        raise PermissionError(r["reason"])

    db.write("research_findings", results)
    guard.log_action(action="write:database", resource="research_findings",
                     allowed=True, result="success",
                     metadata={"rows": len(results)})
```

---

## Framework Integrations

### LangGraph

```python
from agentguard import AgentGuardClient
from langgraph.graph import StateGraph
from typing import TypedDict

guard = AgentGuardClient(base_url="...", agent_key="agk_...")

class AgentState(TypedDict):
    query: str
    results: list
    status: str

def web_search_node(state: AgentState) -> AgentState:
    decision = guard.enforce(action="search:web", resource=state["query"])

    if not decision["allowed"]:
        guard.log_action(action="search:web", resource=state["query"],
                         allowed=False, result="error")
        return {**state, "status": f"blocked: {decision['reason']}"}

    results = run_search(state["query"])
    guard.log_action(action="search:web", resource=state["query"],
                     allowed=True, result="success",
                     metadata={"count": len(results)})
    return {**state, "results": results, "status": "searched"}

def db_write_node(state: AgentState) -> AgentState:
    decision = guard.enforce(action="write:database", resource="research_findings")

    if not decision["allowed"]:
        guard.log_action(action="write:database", resource="research_findings",
                         allowed=False, result="error")
        return {**state, "status": f"blocked: {decision['reason']}"}

    write_to_db(state["results"])
    guard.log_action(action="write:database", resource="research_findings",
                     allowed=True, result="success")
    return {**state, "status": "done"}

builder = StateGraph(AgentState)
builder.add_node("search", web_search_node)
builder.add_node("save",   db_write_node)
builder.set_entry_point("search")
builder.add_edge("search", "save")
graph = builder.compile()
```

### AutoGen

```python
from agentguard import AgentGuardClient
import autogen

guard = AgentGuardClient(base_url="...", agent_key="agk_...")

def guarded_tool(action: str, resource: str, fn, *args, **kwargs):
    """Wrap any AutoGen tool with an AgentGuard permission check."""
    decision = guard.enforce(action=action, resource=resource)
    if not decision["allowed"]:
        guard.log_action(action=action, resource=resource,
                         allowed=False, result="error",
                         metadata={"reason": decision["reason"]})
        return f"[BLOCKED] {decision['reason']}"

    result = fn(*args, **kwargs)
    guard.log_action(action=action, resource=resource,
                     allowed=True, result="success")
    return result

# Wrap your tools
def search_web(query: str) -> str:
    return guarded_tool("search:web", query, _actual_search, query)

def write_db(table: str, data: dict) -> str:
    return guarded_tool("write:database", table, _actual_write, table, data)

# Register with AutoGen as usual
assistant = autogen.AssistantAgent(
    name="ResearchAssistant",
    llm_config={"functions": [
        {"name": "search_web", "description": "Search the web", ...},
        {"name": "write_db",   "description": "Write to database", ...},
    ]}
)
```

### CrewAI

```python
from agentguard import AgentGuardClient
from crewai import Agent, Task, Crew
from crewai_tools import BaseTool

guard = AgentGuardClient(base_url="...", agent_key="agk_...")

class GuardedSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for research findings"

    def _run(self, query: str) -> str:
        decision = guard.enforce(action="search:web", resource=query)
        if not decision["allowed"]:
            guard.log_action(action="search:web", resource=query,
                             allowed=False, result="error")
            return f"[BLOCKED by AgentGuard] {decision['reason']}"

        results = run_search(query)
        guard.log_action(action="search:web", resource=query,
                         allowed=True, result="success",
                         metadata={"count": len(results)})
        return str(results)

class GuardedDBTool(BaseTool):
    name: str = "Database Write"
    description: str = "Save findings to the database"

    def _run(self, table: str, data: str) -> str:
        decision = guard.enforce(action="write:database", resource=table)
        if not decision["allowed"]:
            guard.log_action(action="write:database", resource=table,
                             allowed=False, result="error")
            return f"[BLOCKED by AgentGuard] {decision['reason']}"

        write_to_db(table, data)
        guard.log_action(action="write:database", resource=table,
                         allowed=True, result="success")
        return f"Wrote to {table}"

researcher = Agent(
    role="Research Analyst",
    goal="Research topics and save findings",
    tools=[GuardedSearchTool(), GuardedDBTool()]
)
```

---

## Policy Language

Policies are deny-first with wildcard support.

```python
admin.set_policy(
    agent_id=agent_id,
    allow=[
        # Allow reading any file
        {"action": "read:file",      "resource": "*"},
        # Allow writing only to specific S3 path
        {"action": "write:s3",       "resource": "s3://my-bucket/reports/*"},
        # Allow calling internal APIs
        {"action": "call:api",       "resource": "api.internal.com/*"},
    ],
    deny=[
        # Deny all deletes — always
        {"action": "delete:*",       "resource": "*"},
        # Deny touching the payments table even if an allow rule matches
        {"action": "write:database", "resource": "payments"},
        # Deny access to prod secrets
        {"action": "read:secret",    "resource": "prod/*"},
    ]
)
```

**Evaluation order:**
1. If no policy exists → **DENY** (default deny)
2. Check deny rules → if matched → **DENY**
3. Check allow rules → if matched → **ALLOW**
4. No match → **DENY** (default deny)

**Action formats — type naturally:**

```python
# All of these are equivalent:
{"action": "read:file"}   # standard
{"action": "read file"}   # natural language
{"action": "readFile"}    # camelCase
{"action": "read-file"}   # hyphenated
{"action": "read_file"}   # snake_case
{"action": "Read File"}   # capitalised
```

---

## API Reference

### `AgentGuardClient(base_url, admin_key=None, agent_key=None)`

| Parameter   | Type  | Description |
|-------------|-------|-------------|
| `base_url`  | `str` | URL of your AgentGuard instance |
| `admin_key` | `str` | Admin key — for management operations |
| `agent_key` | `str` | Agent key — for enforce and logging |

### Admin methods

| Method | Description |
|--------|-------------|
| `create_agent(name, owner_team, environment)` | Create a new agent. Returns `agent_id` and `api_key` (shown once). |
| `set_policy(agent_id, allow, deny)` | Set or replace the agent's policy. |
| `get_policy(agent_id)` | Get the current policy. |
| `list_agents(environment, skip, limit)` | List all agents. |
| `get_agent(agent_id)` | Get agent details. |
| `delete_agent(agent_id)` | Delete an agent. |

### Agent methods

| Method | Description |
|--------|-------------|
| `enforce(action, resource, context)` | Check if action is allowed. Returns `{"allowed": bool, "reason": str}`. |
| `log_action(action, allowed, result, resource, context, metadata, request_id)` | Write an audit log entry. |
| `query_logs(agent_id, action, allowed, start_time, end_time, limit, offset)` | Query the audit trail. |

---

## Self-Hosting

The SDK connects to an AgentGuard control plane. To run one locally:

```bash
git clone https://github.com/agentguard/agentguard
cd agentguard
docker compose up -d
```

Backend runs at `http://localhost:8000`. Default admin key: set in `.env`.

See [agentguard/agentguard](https://github.com/agentguard/agentguard) for the full self-hosted setup guide.

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for anything non-trivial.

```bash
git clone https://github.com/agentguard/agentguard-sdk
cd agentguard-sdk
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE).

---

*AgentGuard is IAM for AI agents. The same way you wouldn't give every human employee root database access, you shouldn't give every AI agent unchecked access to your production systems.*
