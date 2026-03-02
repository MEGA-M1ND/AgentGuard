"""Policy management endpoints"""
import json
import anthropic
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.policy import Policy
from app.schemas.policy import (
    PolicyGenerateRequest,
    PolicyGenerateResponse,
    PolicyRequest,
    PolicyResponse,
)
from app.utils.logger import logger

router = APIRouter(prefix="/agents/{agent_id}/policy", tags=["policies"])
templates_router = APIRouter(prefix="/policy-templates", tags=["policies"])

# ── Policy templates ──────────────────────────────────────────────────────────

POLICY_TEMPLATES = [
    {
        "id": "read-only",
        "name": "Read-Only Agent",
        "description": "Can read and list any resource. All writes, deletes, and executions are blocked. Safe for audit bots and monitoring agents.",
        "tags": ["safe", "audit", "compliance", "read-only"],
        "allow": [
            {"action": "read:*",  "resource": "*"},
            {"action": "list:*",  "resource": "*"},
            {"action": "query:*", "resource": "*"},
        ],
        "deny": [
            {"action": "write:*",   "resource": "*"},
            {"action": "delete:*",  "resource": "*"},
            {"action": "execute:*", "resource": "*"},
            {"action": "send:*",    "resource": "*"},
        ],
        "require_approval": [],
    },
    {
        "id": "research-agent",
        "name": "Research Agent",
        "description": "Can search the web and write to the research database. Sensitive tables (users, payments, logs) are blocked. Delete operations require human approval.",
        "tags": ["research", "web-search", "database"],
        "allow": [
            {"action": "search:web",     "resource": "*"},
            {"action": "read:*",         "resource": "*"},
            {"action": "write:database", "resource": "research_findings"},
        ],
        "deny": [
            {"action": "write:database", "resource": "users"},
            {"action": "write:database", "resource": "payments"},
            {"action": "write:database", "resource": "logs"},
            {"action": "execute:*",      "resource": "*"},
        ],
        "require_approval": [
            {"action": "delete:*", "resource": "*"},
        ],
    },
    {
        "id": "data-analyst",
        "name": "Data Analyst",
        "description": "Full read access to query all databases and read files. No writes or deletes. Email reports are allowed.",
        "tags": ["analytics", "reporting", "read-only"],
        "allow": [
            {"action": "read:*",    "resource": "*"},
            {"action": "query:*",   "resource": "*"},
            {"action": "list:*",    "resource": "*"},
            {"action": "send:email", "resource": "reports/*"},
        ],
        "deny": [
            {"action": "write:*",   "resource": "*"},
            {"action": "delete:*",  "resource": "*"},
            {"action": "execute:*", "resource": "*"},
        ],
        "require_approval": [],
    },
    {
        "id": "devops-agent",
        "name": "DevOps Agent",
        "description": "Can deploy, restart, and monitor services. Production deletes and destructive changes require human approval. Database writes are blocked.",
        "tags": ["devops", "deployment", "production"],
        "allow": [
            {"action": "deploy:service",  "resource": "*"},
            {"action": "restart:service", "resource": "*"},
            {"action": "read:*",          "resource": "*"},
            {"action": "query:*",         "resource": "metrics/*"},
        ],
        "deny": [
            {"action": "write:database", "resource": "*"},
            {"action": "execute:script", "resource": "production/*"},
        ],
        "require_approval": [
            {"action": "delete:*",    "resource": "production/*"},
            {"action": "deploy:*",    "resource": "production/*"},
        ],
    },
    {
        "id": "customer-support",
        "name": "Customer Support Agent",
        "description": "Can read customer tickets and send support emails. Billing and payment tables are read-only. All writes to sensitive data require approval.",
        "tags": ["support", "email", "customer-facing"],
        "allow": [
            {"action": "read:*",     "resource": "tickets/*"},
            {"action": "read:*",     "resource": "customers/*"},
            {"action": "send:email", "resource": "customers/*"},
            {"action": "write:*",    "resource": "tickets/*"},
        ],
        "deny": [
            {"action": "write:*",  "resource": "payments/*"},
            {"action": "delete:*", "resource": "customers/*"},
            {"action": "execute:*", "resource": "*"},
        ],
        "require_approval": [
            {"action": "write:*",  "resource": "customers/*"},
            {"action": "read:*",   "resource": "payments/*"},
        ],
    },
    {
        "id": "full-access-dev",
        "name": "Full Access (Development Only)",
        "description": "Allows all actions on all resources. Use only in development environments. Never use in production.",
        "tags": ["development", "testing", "unrestricted"],
        "allow": [
            {"action": "*", "resource": "*"},
        ],
        "deny": [],
        "require_approval": [],
    },
]


@templates_router.get("")
def list_policy_templates() -> List[dict]:
    """
    Return all built-in policy templates (Admin only).

    Templates provide pre-configured allow/deny/require_approval rule sets
    for common agent archetypes. Apply a template via the policy editor
    in the UI, then customise as needed before saving.
    """
    return POLICY_TEMPLATES


_GENERATE_SYSTEM_PROMPT = """You are a security policy parser for AgentGuard, an AI agent governance platform.

Given a natural language description of what an AI agent should and should not be able to do, extract structured allow and deny rules.

Rules follow this format:
- action: a verb:noun pattern like "read:file", "write:database", "send:email", "delete:*", "search:web", "execute:code"
- resource: a resource pattern like "*", "database/users", "s3://bucket/*", "production/*"

Common action verbs: read, write, delete, execute, send, query, search, access, modify, create, update, browse

Guidelines:
- Use "*" as the resource when not specified or when it applies broadly
- Prefer specific deny rules over broad ones when possible
- Default to deny-first: only allow what is explicitly permitted
- Use wildcard "*" in action noun only when the description is truly broad (e.g., "delete anything" → "delete:*")
- Keep the explanation concise (1-2 sentences)

Respond ONLY with valid JSON in this exact format, no markdown, no extra text:
{
  "allow": [
    {"action": "verb:noun", "resource": "*"}
  ],
  "deny": [
    {"action": "verb:noun", "resource": "*"}
  ],
  "explanation": "Brief explanation of the generated policy"
}"""


@router.post("/generate", response_model=PolicyGenerateResponse)
def generate_policy(
    agent_id: str,
    data: PolicyGenerateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """
    Generate policy rules from a natural language description using Claude AI (Admin only).

    Returns proposed allow/deny rules for human review before applying.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI policy generation is not configured. Set ANTHROPIC_API_KEY in backend/.env",
        )

    # Verify agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        user_message = (
            f"Agent name: {agent.name}\n"
            f"Agent description: {data.description}\n\n"
            "Generate the appropriate allow and deny policy rules for this agent."
        )

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_GENERATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        allow_rules = [
            {"action": r.get("action", ""), "resource": r.get("resource", "*")}
            for r in parsed.get("allow", [])
            if r.get("action")
        ]
        deny_rules = [
            {"action": r.get("action", ""), "resource": r.get("resource", "*")}
            for r in parsed.get("deny", [])
            if r.get("action")
        ]
        explanation = parsed.get("explanation", "Policy generated from description.")

        logger.info(
            f"Generated policy for agent: {agent_id}",
            extra={"agent_id": agent_id, "action": "generate_policy"},
        )

        return PolicyGenerateResponse(
            allow=allow_rules,
            deny=deny_rules,
            explanation=explanation,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON for policy generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unparseable response. Please try again.",
        )
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )


@router.put("", response_model=PolicyResponse)
def set_policy(
    agent_id: str,
    policy_data: PolicyRequest,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Set or update policy for an agent (Admin only)

    Replaces existing policy if present
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found or inactive"
        )

    # Convert Pydantic models to dicts
    allow_rules = [rule.model_dump() for rule in policy_data.allow]
    deny_rules = [rule.model_dump() for rule in policy_data.deny]
    require_approval_rules = [rule.model_dump() for rule in policy_data.require_approval]

    # Check if policy exists
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()

    if policy:
        # Update existing policy
        # flag_modified is required for SQLAlchemy to detect JSON column changes —
        # bare assignment is not always tracked as "dirty" on mutable JSON columns
        from sqlalchemy.orm.attributes import flag_modified
        policy.allow_rules = allow_rules
        policy.deny_rules = deny_rules
        policy.require_approval_rules = require_approval_rules
        flag_modified(policy, "allow_rules")
        flag_modified(policy, "deny_rules")
        flag_modified(policy, "require_approval_rules")
    else:
        # Create new policy
        policy = Policy(
            agent_id=agent_id,
            allow_rules=allow_rules,
            deny_rules=deny_rules,
            require_approval_rules=require_approval_rules,
        )
        db.add(policy)

    db.commit()
    db.refresh(policy)

    logger.info(
        f"Set policy for agent: {agent_id}",
        extra={"agent_id": agent_id, "action": "set_policy"}
    )

    return PolicyResponse(
        agent_id=policy.agent_id,
        allow=policy.allow_rules,
        deny=policy.deny_rules,
        require_approval=getattr(policy, "require_approval_rules", None) or [],
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.get("", response_model=PolicyResponse)
def get_policy(
    agent_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Get policy for an agent (Admin only)
    """
    # Check if agent exists
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )

    # Get policy
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No policy found for agent {agent_id}"
        )

    return PolicyResponse(
        agent_id=policy.agent_id,
        allow=policy.allow_rules,
        deny=policy.deny_rules,
        require_approval=getattr(policy, "require_approval_rules", None) or [],
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )
