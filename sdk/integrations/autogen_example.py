"""
AgentGuard + AutoGen Integration Example
=========================================
Wraps AutoGen tool functions with AgentGuard permission checks.
The pattern: every tool calls guard.enforce() before executing.

Install:
    pip install agentguard-sdk pyautogen

Usage:
    export AGENTGUARD_URL=http://localhost:8000
    export AGENTGUARD_AGENT_KEY=agk_your_key
    python autogen_example.py
"""
import os
from functools import wraps
from typing import Any, Callable

from agentguard import AgentGuardClient

# ── AgentGuard client ─────────────────────────────────────────────────────────

guard = AgentGuardClient(
    base_url=os.environ.get("AGENTGUARD_URL", "http://localhost:8000"),
    agent_key=os.environ.get("AGENTGUARD_AGENT_KEY", ""),
)

# ── Guard decorator ───────────────────────────────────────────────────────────

def guarded(action: str, resource: str) -> Callable:
    """
    Decorator that wraps any function with an AgentGuard permission check.

    Usage:
        @guarded("read:file", "reports/*")
        def read_report(path: str) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            decision = guard.enforce(action=action, resource=resource)

            if not decision["allowed"]:
                guard.log_action(
                    action=action, resource=resource,
                    allowed=False, result="error",
                    metadata={"reason": decision["reason"]},
                )
                return f"[BLOCKED by AgentGuard] {decision['reason']}"

            result = fn(*args, **kwargs)

            guard.log_action(
                action=action, resource=resource,
                allowed=True, result="success",
            )
            return result
        return wrapper
    return decorator

# ── Tools with guard protection ───────────────────────────────────────────────

@guarded("search:web", "*")
def search_web(query: str) -> str:
    """Search the web. Blocked if agent policy denies search:web."""
    # Replace with Tavily, SerpAPI, Bing, etc.
    return f"[mock] Top results for '{query}': result1, result2, result3"


@guarded("write:database", "research_findings")
def save_to_database(data: str) -> str:
    """Save data to research_findings. Blocked if policy denies write:database."""
    # Replace with your actual DB client
    return f"[mock] Saved to research_findings: {data[:50]}..."


@guarded("send:email", "support/*")
def send_email(to: str, body: str) -> str:
    """Send an email. Blocked if policy denies send:email on support/*."""
    return f"[mock] Email sent to {to}"


# ── AutoGen agent setup ───────────────────────────────────────────────────────

try:
    import autogen

    llm_config = {
        "config_list": [{"model": "gpt-4", "api_key": os.environ.get("OPENAI_API_KEY", "")}],
        "functions": [
            {
                "name": "search_web",
                "description": "Search the web for information on a topic",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "save_to_database",
                "description": "Save research findings to the database",
                "parameters": {
                    "type": "object",
                    "properties": {"data": {"type": "string"}},
                    "required": ["data"],
                },
            },
        ],
    }

    assistant = autogen.AssistantAgent(
        name="GuardedResearchAssistant",
        llm_config=llm_config,
        system_message=(
            "You are a research assistant. Use search_web to find information, "
            "then save_to_database to persist your findings."
        ),
    )

    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        human_input_mode="NEVER",
        function_map={
            "search_web":       search_web,
            "save_to_database": save_to_database,
        },
    )

    print("AutoGen agent configured with AgentGuard governance.")
    print("All tool calls are permission-checked before execution.")

except ImportError:
    # AutoGen not installed — demonstrate the pattern standalone
    print("AutoGen not installed. Demonstrating guarded tools directly:\n")

    print("search_web('AI governance') →", search_web("AI governance"))
    print("save_to_database('findings') →", save_to_database("key findings from research"))
    print("\nView audit trail: http://localhost:3000/logs")
