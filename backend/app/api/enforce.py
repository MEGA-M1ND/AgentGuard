"""Policy enforcement endpoint"""
import fnmatch
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_agent
from app.database import get_db
from app.models.agent import Agent
from app.models.approval import ApprovalRequest
from app.models.policy import Policy
from app.models.team_policy import TeamPolicy
from app.schemas.policy import EnforceRequest, EnforceResponse
from app.utils.logger import logger
from app.utils.webhook import send_webhook

router = APIRouter(prefix="/enforce", tags=["enforcement"])


def normalize_action(action: str) -> str:
    """
    Intelligently normalize action strings to verb:noun pattern.

    Supports multiple user-friendly input formats:
    - Standard: "read:file" → "read:file"
    - Spaces: "read file" → "read:file"
    - Hyphens: "read-file" → "read:file"
    - Underscores: "read_file" → "read:file"
    - CamelCase: "readFile" → "read:file"
    - Natural: "Read File" → "read:file"
    - Mixed: "Read-File" → "read:file"
    - Single word: "read" → "read" (for wildcard matching)
    - Wildcards preserved: "delete *" → "delete:*"
    """
    import re

    action = action.strip()

    if ":" in action:
        return action.lower()

    action = re.sub(r'([a-z])([A-Z])', r'\1 \2', action)
    action = action.lower()
    action = action.replace("-", " ").replace("_", " ")

    parts = [p for p in action.split() if p]

    if len(parts) == 1:
        return parts[0]

    verb = parts[0]
    noun = parts[1]

    return f"{verb}:{noun}"


def matches_rule(action: str, resource: str, rule: dict, agent: Agent) -> bool:
    """
    Check if action/resource matches a policy rule, including optional conditions.

    Performs action/resource glob matching then evaluates any ``conditions`` block
    (env, time_range, day_of_week) via :func:`app.utils.conditions.evaluate_conditions`.
    Returns True only when *both* the action/resource pattern *and* all conditions pass.
    """
    from app.utils.conditions import evaluate_conditions

    rule_action = rule.get("action", "")
    rule_resource = rule.get("resource", "*")

    normalized_action = normalize_action(action)
    normalized_rule = normalize_action(rule_action)

    matched = False
    if fnmatch.fnmatch(normalized_action, normalized_rule):
        if not rule_resource or rule_resource == "*":
            matched = True
        else:
            matched = fnmatch.fnmatch(resource.lower() if resource else "", rule_resource.lower())
    elif ":" not in normalized_action and ":" in normalized_rule:
        rule_verb = normalized_rule.split(":")[0]
        if normalized_action == rule_verb or fnmatch.fnmatch(normalized_action, rule_verb):
            if not rule_resource or rule_resource == "*":
                matched = True
            else:
                matched = fnmatch.fnmatch(resource.lower() if resource else "", rule_resource.lower())

    if not matched:
        return False

    return evaluate_conditions(rule.get("conditions") or {}, agent, None)


def enforce_policy(
    agent_id: str,
    action: str,
    resource: str,
    context: Optional[Dict[str, Any]],
    db: Session,
    agent: Optional[Agent] = None,
) -> tuple[str, str, Optional[str]]:
    """
    Enforce policy for an agent action.

    Returns:
        Tuple of (status: str, reason: str, approval_id: Optional[str])
        status is one of: "allowed", "denied", "pending"

    Policy logic (priority order):
    1. If no policy exists, deny by default
    2. Check require_approval rules first — if matched, create approval request and return pending
    3. Check deny rules — if matched, deny
    4. Check allow rules — if matched, allow
    5. Default: deny-list mode if no allow rules configured (allow anything not denied);
               allow-list mode if allow rules present (deny anything not explicitly allowed)
    """
    policy = db.query(Policy).filter(Policy.agent_id == agent_id).first()

    if not policy:
        return "denied", "No policy defined for agent (default deny)", None

    # Resolve the Agent object — needed for condition evaluation, team policy lookup, and webhook payload.
    # The caller may pass it directly to avoid a second DB round-trip.
    if agent is None:
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

    # ------------------------------------------------------------------
    # Team policy merge
    # ------------------------------------------------------------------
    # If the agent's owner_team has a TeamPolicy, merge its rules with the
    # agent's own policy.  Merge semantics:
    #   - deny:             team deny goes FIRST  (team can block agent allow)
    #   - allow:            agent allow goes FIRST (agent can narrow team allow)
    #   - require_approval: agent rules first, team rules appended
    # ------------------------------------------------------------------
    team_policy = None
    if agent and agent.owner_team:
        team_policy = db.query(TeamPolicy).filter(TeamPolicy.team == agent.owner_team).first()

    if team_policy:
        merged_require_approval = (
            (getattr(policy, "require_approval_rules", None) or []) +
            (team_policy.require_approval_rules or [])
        )
        merged_deny = (team_policy.deny_rules or []) + (policy.deny_rules or [])
        merged_allow = (policy.allow_rules or []) + (team_policy.allow_rules or [])
    else:
        merged_require_approval = getattr(policy, "require_approval_rules", None) or []
        merged_deny = policy.deny_rules or []
        merged_allow = policy.allow_rules or []

    # 1. Check require_approval rules first
    for rule in merged_require_approval:
        if matches_rule(action, resource or "", rule, agent):
            # Create an ApprovalRequest record
            approval = ApprovalRequest(
                agent_id=agent_id,
                action=action,
                resource=resource or None,
                context=context,
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)

            # Fire webhook notification (non-blocking)
            send_webhook("approval.created", {
                "approval_id": approval.approval_id,
                "agent_id": agent_id,
                "agent_name": agent.name if agent else None,
                "action": action,
                "resource": resource or None,
                "context": context,
            })

            reason = f"Requires human approval: {rule.get('action')} on {rule.get('resource', '*')}"
            return "pending", reason, approval.approval_id

    # 2. Check deny rules
    for rule in merged_deny:
        if matches_rule(action, resource or "", rule, agent):
            return "denied", f"Denied by rule: {rule.get('action')} on {rule.get('resource', '*')}", None

    # 3. Check allow rules
    for rule in merged_allow:
        if matches_rule(action, resource or "", rule, agent):
            return "allowed", f"Allowed by rule: {rule.get('action')} on {rule.get('resource', '*')}", None

    # 4. Default: mode depends on whether allow rules are configured.
    #    - Allow-list mode (allow rules present): deny anything not explicitly allowed.
    #    - Deny-list mode (no allow rules): allow anything not explicitly denied.
    if merged_allow:
        return "denied", "No matching allow rule (default deny)", None
    return "allowed", "No deny rule matched (default allow — deny-list mode)", None


@router.post("", response_model=EnforceResponse)
def enforce(
    request: EnforceRequest,
    agent: Agent = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Check if agent is allowed to perform an action (Agent auth).

    Returns status: 'allowed', 'denied', or 'pending'.
    When status='pending', poll GET /approvals/{approval_id} until decision is made.
    """
    action_status, reason, approval_id = enforce_policy(
        agent_id=agent.agent_id,
        action=request.action,
        resource=request.resource or "",
        context=request.context,
        db=db,
        agent=agent,
    )

    allowed = action_status == "allowed"

    logger.info(
        f"Enforcement check: {agent.agent_id} - {request.action} - {action_status}",
        extra={
            "agent_id": agent.agent_id,
            "action": request.action,
            "resource": request.resource,
            "allowed": allowed,
            "status": action_status,
            "approval_id": approval_id,
        }
    )

    return EnforceResponse(
        allowed=allowed,
        status=action_status,
        reason=reason,
        approval_id=approval_id,
    )


@router.get("/approval/{approval_id}")
def get_own_approval_status(
    approval_id: str,
    agent: Agent = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """
    Poll approval status for an approval created by this agent (Agent auth).

    Agents can only view approvals they created — no admin credentials required.
    Returns status ('pending', 'approved', 'denied') and decision details once
    a human has acted on the request.
    """
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.approval_id == approval_id,
        ApprovalRequest.agent_id == agent.agent_id,
    ).first()

    if not approval:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found for this agent",
        )

    return {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "decision_reason": approval.decision_reason,
        "decision_by": approval.decision_by,
        "decision_at": approval.decision_at.isoformat() if approval.decision_at else None,
    }


def enforce_or_raise(
    agent_id: str,
    action: str,
    resource: str,
    db: Session
) -> None:
    """
    Helper function to enforce policy and raise exception if denied.

    Raises:
        HTTPException: If action is not allowed or pending
    """
    action_status, reason, _ = enforce_policy(agent_id, action, resource, None, db)

    if action_status != "allowed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action not allowed: {reason}"
        )
