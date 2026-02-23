"""
AgentGuard + CrewAI Integration Example
========================================
Wraps CrewAI tools with AgentGuard permission checks.
Each tool checks guard.enforce() before running.

Install:
    pip install agentguard-sdk crewai crewai-tools

Usage:
    export AGENTGUARD_URL=http://localhost:8000
    export AGENTGUARD_AGENT_KEY=agk_your_key
    python crewai_example.py
"""
import os
from typing import Optional, Type

from agentguard import AgentGuardClient
from pydantic import BaseModel

# ── AgentGuard client ─────────────────────────────────────────────────────────

guard = AgentGuardClient(
    base_url=os.environ.get("AGENTGUARD_URL", "http://localhost:8000"),
    agent_key=os.environ.get("AGENTGUARD_AGENT_KEY", ""),
)

# ── Tool schemas ──────────────────────────────────────────────────────────────

class SearchInput(BaseModel):
    query: str

class DatabaseWriteInput(BaseModel):
    table: str
    data:  str

class FileReadInput(BaseModel):
    path: str

# ── Guarded CrewAI tools ──────────────────────────────────────────────────────

try:
    from crewai_tools import BaseTool

    class GuardedWebSearchTool(BaseTool):
        name:        str = "Web Search"
        description: str = "Search the web for research on any topic."
        args_schema: Type[BaseModel] = SearchInput

        def _run(self, query: str) -> str:
            decision = guard.enforce(action="search:web", resource=query)

            if not decision["allowed"]:
                guard.log_action(
                    action="search:web", resource=query,
                    allowed=False, result="error",
                    metadata={"reason": decision["reason"]},
                )
                return f"[BLOCKED by AgentGuard] {decision['reason']}"

            # Replace with Tavily, SerpAPI, etc.
            results = f"[mock] Top results for '{query}': result1, result2"
            guard.log_action(
                action="search:web", resource=query,
                allowed=True, result="success",
            )
            return results


    class GuardedDatabaseWriteTool(BaseTool):
        name:        str = "Database Write"
        description: str = "Write research findings to a database table."
        args_schema: Type[BaseModel] = DatabaseWriteInput

        def _run(self, table: str, data: str) -> str:
            decision = guard.enforce(action="write:database", resource=table)

            if not decision["allowed"]:
                guard.log_action(
                    action="write:database", resource=table,
                    allowed=False, result="error",
                    metadata={"reason": decision["reason"]},
                )
                return f"[BLOCKED by AgentGuard] {decision['reason']}"

            # Replace with your actual DB client
            guard.log_action(
                action="write:database", resource=table,
                allowed=True, result="success",
                metadata={"table": table},
            )
            return f"Successfully wrote to {table}"


    class GuardedFileReadTool(BaseTool):
        name:        str = "File Reader"
        description: str = "Read the contents of a file."
        args_schema: Type[BaseModel] = FileReadInput

        def _run(self, path: str) -> str:
            decision = guard.enforce(action="read:file", resource=path)

            if not decision["allowed"]:
                guard.log_action(
                    action="read:file", resource=path,
                    allowed=False, result="error",
                    metadata={"reason": decision["reason"]},
                )
                return f"[BLOCKED by AgentGuard] {decision['reason']}"

            # Replace with actual file read
            guard.log_action(
                action="read:file", resource=path,
                allowed=True, result="success",
            )
            return f"[mock] Contents of {path}: ..."


    # ── CrewAI agent & crew setup ─────────────────────────────────────────────

    from crewai import Agent, Crew, Task

    researcher = Agent(
        role="Research Analyst",
        goal="Research topics thoroughly and save your findings",
        backstory="You are an expert analyst who researches topics and documents findings.",
        tools=[
            GuardedWebSearchTool(),
            GuardedDatabaseWriteTool(),
            GuardedFileReadTool(),
        ],
        verbose=True,
    )

    research_task = Task(
        description="Research the latest trends in AI agent frameworks and save to research_findings",
        expected_output="A summary of findings saved to the database",
        agent=researcher,
    )

    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True,
    )

    print("CrewAI crew configured with AgentGuard governance.")
    print("All tool calls are permission-checked before execution.")
    print("Run crew.kickoff() to start.")

except ImportError:
    # crewai not installed — show pattern directly
    print("crewai-tools not installed. Demonstrating guarded tool pattern:\n")

    # Simulate what the tool's _run method does
    def demo_guarded_tool(action: str, resource: str) -> str:
        decision = guard.enforce(action=action, resource=resource)
        if not decision["allowed"]:
            guard.log_action(action=action, resource=resource,
                             allowed=False, result="error",
                             metadata={"reason": decision["reason"]})
            return f"[BLOCKED] {decision['reason']}"
        guard.log_action(action=action, resource=resource,
                         allowed=True, result="success")
        return f"[OK] {action} on {resource}"

    print(demo_guarded_tool("search:web",     "AI frameworks 2025"))
    print(demo_guarded_tool("write:database", "research_findings"))
    print(demo_guarded_tool("write:database", "payments"))  # should be denied
    print("\nView audit trail: http://localhost:3000/logs")
